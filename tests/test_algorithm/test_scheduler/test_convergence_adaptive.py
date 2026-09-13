"""ConvergenceAdaptiveScheduler tests — legacy W2 PID + paper-quantity branch.

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm import (
    CodimensionSheetScheduler,
    ConvergenceAdaptiveScheduler,
    PaperRatioAdaptiveScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler import build_scheduler_from_config

# Shared test traces (same as the original monolithic test file).
_W2_TRACE = (0.90, 0.82, 0.79, 0.77, 0.76)
_COVERAGE_TRACE = (0.40, 0.55, 0.62, 0.68, 0.71)
_SELECTION_TRACE = (0.50, 0.61, 0.70, 0.78, 0.83)


def test_convergence_adaptive_scheduler_initial_shift_zero() -> None:
    """A fresh ConvergenceAdaptiveScheduler has shift == 0.0 and no W2 history."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10)
    )
    assert scheduler.shift == 0.0
    assert scheduler.w2_history == ()
    assert scheduler.smoothed_w2 is None
    # First round: shift == 0 -> n_cap == base.sample(0).n_cap.
    base_sample = scheduler.base.sample(0, 0, 0)
    shifted = scheduler.sample(0, 0, 0)
    assert shifted.n_cap == pytest.approx(float(base_sample.n_cap))
    assert shifted.u_r == pytest.approx(float(base_sample.u_r))


def test_convergence_adaptive_scheduler_shift_increases_when_w2_improves() -> None:
    """When W2 improves (delta<0, ratio<1), the shift trends positive.

    F16: ``w2_history`` contains the EMA-smoothed values.
    With ema=0.3:
        round 0: smoothed = 1.0, history = (1.0,)
        round 1: smoothed = 0.3*0.5 + 0.7*1.0 = 0.85, history = (1.0, 0.85)
    """
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.20,
        kd=0.10,
        shift_max=0.5,
        ema=0.3,
    )
    # Round 0: W2 = 1.0 (no shift; first sample).
    scheduler.record_round_feedback(0, {"W2": 1.0})
    assert scheduler.w2_history == (1.0,)
    assert scheduler.shift == 0.0  # no shift after first round
    # Round 1: W2 = 0.5 (improvement; should push shift positive).
    scheduler.record_round_feedback(1, {"W2": 0.5})
    assert scheduler.w2_history == pytest.approx((1.0, 0.85))
    assert scheduler.shift > 0.0
    shift_after_first = scheduler.shift
    # Round 2: W2 = 0.25 (further improvement; shift must trend up).
    scheduler.record_round_feedback(2, {"W2": 0.25})
    assert scheduler.shift > shift_after_first


def test_convergence_adaptive_scheduler_shift_decreases_when_w2_worsens() -> None:
    """When W2 worsens (delta>0, ratio>1), the shift trends negative."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.20,
        kd=0.10,
        shift_max=0.5,
        ema=0.3,
    )
    scheduler.record_round_feedback(0, {"W2": 1.0})
    # Round 1: W2 = 1.5 (worsening; should push shift negative).
    scheduler.record_round_feedback(1, {"W2": 1.5})
    assert scheduler.shift < 0.0
    shift_after_first = scheduler.shift
    # Round 2: W2 = 2.0 (further worsening; shift must trend down).
    scheduler.record_round_feedback(2, {"W2": 2.0})
    assert scheduler.shift < shift_after_first


# ---------------------------------------------------------------------------
# F16 — PID uses smoothed_w2 as the prev reference (P0)
# ---------------------------------------------------------------------------


def test_pid_uses_smoothed_w2_as_prev() -> None:
    """F16: ``ConvergenceAdaptiveScheduler``'s PID reads its ``prev``
    reference from the EMA-smoothed series (``_smoothed_w2``), not the
    raw aggregated W2 signal.

    With ema=0.3, after rounds ``W2 = [1.0, 0.5, 0.25]`` the
    ``smoothed_w2`` is the EMA at each step. The PID ``prev`` on round 2
    is the smoothed value at round 1 (``0.85``), not the raw ``0.5``.
    """
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.0,  # disable proportional term; isolate delta/prev
        kd=0.0,
        shift_max=0.5,
        ema=0.3,
    )
    # Round 0.
    scheduler.record_round_feedback(0, {"W2": 1.0})
    assert scheduler.smoothed_w2 == pytest.approx(1.0)
    # Round 1 — smoothed = 0.3 * 0.5 + 0.7 * 1.0 = 0.85.
    scheduler.record_round_feedback(1, {"W2": 0.5})
    assert scheduler.smoothed_w2 == pytest.approx(0.85)
    # F16: w2_history contains the smoothed value, NOT the raw 0.5.
    assert scheduler.w2_history[-1] == pytest.approx(0.85)
    assert scheduler.w2_history[-1] != pytest.approx(0.5)


def test_convergence_adaptive_scheduler_shift_bounded() -> None:
    """The shift never exceeds shift_max, even under extreme W2 swings."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=5.0,
        kd=5.0,
        shift_max=0.15,
        ema=0.3,
    )
    # Extreme improvement: W2 collapsing from 100.0 -> 1e-9.
    scheduler.record_round_feedback(0, {"W2": 100.0})
    scheduler.record_round_feedback(1, {"W2": 1e-9})
    assert scheduler.shift <= scheduler.shift_max
    assert scheduler.shift >= -scheduler.shift_max
    # Extreme worsening: W2 exploding from 1e-9 -> 100.0.
    scheduler.reset()
    scheduler.record_round_feedback(0, {"W2": 1e-9})
    scheduler.record_round_feedback(1, {"W2": 100.0})
    assert scheduler.shift >= -scheduler.shift_max
    assert scheduler.shift <= scheduler.shift_max


def test_convergence_adaptive_scheduler_ema_smoothing() -> None:
    """EMA smooths noisy W2 values: smoothed_w2 sits between extremes."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.0,
        kd=0.0,
        shift_max=0.5,
        ema=0.5,
    )
    # Feed alternating high / low values. EMA(0.5) is a centred
    # smoothing; the result after several alternations sits strictly
    # between the raw extremes, never equal to either raw value.
    raw_values = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    for r, w2 in enumerate(raw_values):
        scheduler.record_round_feedback(r, {"W2": float(w2)})
    smoothed = scheduler.smoothed_w2
    assert smoothed is not None
    assert 0.0 < smoothed < 1.0  # strictly between extremes


def test_convergence_adaptive_scheduler_n_cap_in_unit_interval() -> None:
    """After many feedback calls, every n_cap lies in [0, 1]."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=11),
        kp=1.0,
        kd=1.0,
        shift_max=2.0,
        ema=0.5,
    )
    # Alternate extreme W2 values to push shift around.
    w2_series = [10.0, 1e-6, 10.0, 1e-6, 10.0, 1e-6, 10.0, 1e-6, 10.0, 1e-6]
    for r, w2 in enumerate(w2_series):
        scheduler.record_round_feedback(r, {"W2": float(w2)})
    # Sample every round and assert n_cap is in the canonical range.
    for r in range(scheduler.cycle_length()):
        sample = scheduler.sample(0, r, r)
        assert 0.0 <= float(sample.n_cap) <= 1.0
        assert 0.0 <= float(sample.u_r) <= 1.0


def test_convergence_adaptive_scheduler_byte_deterministic_under_same_w2_series() -> None:
    """Same W2 series + same base scheduler -> identical n_cap trajectories."""
    base_a = default_cosine_scheduler(cycle_length=12)
    base_b = default_cosine_scheduler(cycle_length=12)
    a = ConvergenceAdaptiveScheduler(base=base_a, kp=0.1, kd=0.05, shift_max=0.2)
    b = ConvergenceAdaptiveScheduler(base=base_b, kp=0.1, kd=0.05, shift_max=0.2)
    series = [1.0, 0.7, 0.6, 0.8, 0.5, 0.4, 0.3, 0.2]
    for r, w2 in enumerate(series):
        a.record_round_feedback(r, {"W2": float(w2)})
        b.record_round_feedback(r, {"W2": float(w2)})
    n_caps_a = [a.sample(0, r, r).n_cap for r in range(a.cycle_length())]
    n_caps_b = [b.sample(0, r, r).n_cap for r in range(b.cycle_length())]
    assert n_caps_a == n_caps_b


def test_convergence_adaptive_scheduler_reset_clears_state() -> None:
    """reset() clears w2_history, shift, smoothed_w2, and last_sample."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10)
    )
    scheduler.record_round_feedback(0, {"W2": 1.0})
    scheduler.record_round_feedback(1, {"W2": 0.5})
    scheduler.sample(0, 2, 2)
    assert scheduler.w2_history != ()
    assert scheduler.shift != 0.0
    assert scheduler.smoothed_w2 is not None
    assert scheduler.last_sample is not None
    scheduler.reset()
    assert scheduler.w2_history == ()
    assert scheduler.shift == 0.0
    assert scheduler.smoothed_w2 is None
    assert scheduler.last_sample is None


def test_convergence_adaptive_scheduler_schedule_family_and_config_hash() -> None:
    """schedule_family and config_hash must reflect the adaptive identity."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.10,
        kd=0.05,
        shift_max=0.15,
        ema=0.3,
    )
    assert scheduler.schedule_family() == "convergence_adaptive_cosine"
    # config_hash must change with kp / kd / shift_max / ema.
    h0 = scheduler.config_hash()
    alt = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.20,
        kd=0.05,
        shift_max=0.15,
        ema=0.3,
    )
    assert alt.config_hash() != h0
    # Same params -> same hash.
    again = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10),
        kp=0.10,
        kd=0.05,
        shift_max=0.15,
        ema=0.3,
    )
    assert again.config_hash() == h0


def test_convergence_adaptive_scheduler_ignores_non_finite_w2() -> None:
    """Non-finite W2 (NaN / inf) must be ignored — no history update, no shift."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=10)
    )
    scheduler.record_round_feedback(0, {"W2": float("nan")})
    assert scheduler.w2_history == ()
    assert scheduler.shift == 0.0
    scheduler.record_round_feedback(0, {"W2": float("inf")})
    assert scheduler.w2_history == ()
    assert scheduler.shift == 0.0
    # Missing key -> NaN -> ignored.
    scheduler.record_round_feedback(0, {})
    assert scheduler.w2_history == ()


def test_convergence_adaptive_scheduler_build_scheduler_factory() -> None:
    """build_scheduler('convergence_adaptive') returns the adaptive class."""
    from adaptive_reflow.algorithm import build_scheduler

    scheduler = build_scheduler("convergence_adaptive")
    assert isinstance(scheduler, ConvergenceAdaptiveScheduler)
    assert scheduler.schedule_family() == "convergence_adaptive_cosine"
    # And the registry key is normalised case- and whitespace-insensitively.
    scheduler = build_scheduler("  CONVERGENCE_ADAPTIVE  ")
    assert isinstance(scheduler, ConvergenceAdaptiveScheduler)


# ---------------------------------------------------------------------------
# P0-A6 — ConvergenceAdaptiveScheduler multi-metric feedback
# ---------------------------------------------------------------------------


def test_convergence_adaptive_multi_metric() -> None:
    """P0-A6: coverage + selection_ratio move the shift vs. W2-only."""
    w2_only = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=8),
        metric_weights={"W2": 1.0},
    )
    multi = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=8)
    )
    for r, (w2, cov, sel) in enumerate(
        zip(_W2_TRACE, _COVERAGE_TRACE, _SELECTION_TRACE, strict=True)
    ):
        w2_only.record_round_feedback(r, {"W2": w2})
        multi.record_round_feedback(
            r, {"W2": w2, "coverage": cov, "selection_ratio": sel}
        )
    assert multi.last_feedback_keys == ("W2", "coverage", "selection_ratio")
    assert w2_only.last_feedback_keys == ("W2",)
    # Quantitative target: the multi-metric controller lands at least
    # 1e-3 (in u_r units) away from the W2-only controller.
    assert abs(multi.shift - w2_only.shift) >= 1e-3
    # All three metrics improve, so the aggregated loss keeps falling and
    # the controller pushes toward refinement (positive shift).
    assert multi.shift > 0.0


def test_convergence_adaptive_w2_only_matches_legacy() -> None:
    """P0-A6 + F16: a W2-only feedback dict reproduces the legacy signal.

    F16: ``w2_history`` now contains the EMA-smoothed values (the PID
    ``prev`` reference), NOT the raw aggregated signal. The
    ``smoothed_w2`` property still tracks the EMA identically to the
    legacy path.
    """
    default_weights = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=8)
    )
    explicit_w2 = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=8),
        metric_weights={"W2": 1.0},
    )
    for r, w2 in enumerate(_W2_TRACE):
        default_weights.record_round_feedback(r, {"W2": w2})
        explicit_w2.record_round_feedback(r, {"W2": w2})
    # F16: history contains the EMA-smoothed series.
    assert default_weights.w2_history == explicit_w2.w2_history
    assert default_weights.shift == explicit_w2.shift
    assert default_weights.smoothed_w2 == explicit_w2.smoothed_w2
    # Sanity: with the default EMA coefficient, the smoothed series
    # starts equal to the first raw sample.
    assert default_weights.w2_history[0] == pytest.approx(_W2_TRACE[0])


def test_build_scheduler_from_config_respects_kwargs_for_edm() -> None:
    """F23: ``build_scheduler_from_config`` honours the kwargs in the
    ``config`` dict (not just the family key) for the
    previously-unhandled ``edm`` family.
    """
    config = {
        "family": "edm",
        "rho": 99.0,
        "sigma_min": 0.001,
        "sigma_max": 0.5,
        "cycle_length": 16,
        "n_min": 0.0,
        "n_max": 1.0,
        "seed": 7,
    }
    sched = build_scheduler_from_config(config)
    cfg = sched.to_config()
    # ``rho`` MUST be preserved through the round-trip (F23 — the
    # family-specific from_config dispatcher is the canonical
    # deserialiser, not the no-arg ``factory()`` fallback).
    assert cfg.get("rho") == 99.0
    assert cfg.get("sigma_max") == 0.5


def test_convergence_adaptive_default_config_hash_unchanged() -> None:
    """Default weights stay out of the digest (legacy hash preserved)."""
    a = ConvergenceAdaptiveScheduler(base=default_cosine_scheduler())
    b = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(), metric_weights={"W2": 1.0}
    )
    assert a.config_hash() != b.config_hash()
    assert a.metric_weights == {
        "W2": 1.0,
        "coverage": 0.3,
        "selection_ratio": 0.5,
    }


def test_convergence_adaptive_ignores_broken_metrics() -> None:
    """Non-finite / non-numeric feedback never poisons the controller."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4)
    )
    scheduler.record_round_feedback(
        0, {"W2": float("nan"), "coverage": float("inf")}
    )
    assert scheduler.w2_history == ()
    scheduler.record_round_feedback(
        1, {"W2": 0.5, "coverage": "bad", "merge_audit_codes": []}
    )
    assert scheduler.w2_history == (0.5,)
    assert scheduler.last_feedback_keys == ("W2",)


def test_convergence_adaptive_metric_weights_round_trip() -> None:
    """P0-A6 weights survive ``to_config`` / ``from_config``."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4),
        metric_weights={"W2": 1.0, "coverage": 0.25},
    )
    rebuilt = ConvergenceAdaptiveScheduler.from_config(scheduler.to_config())
    assert rebuilt.metric_weights == {"W2": 1.0, "coverage": 0.25}
    assert rebuilt.config_hash() == scheduler.config_hash()


def test_convergence_adaptive_rejects_bad_metric_weights() -> None:
    """Negative / empty weight maps are rejected."""
    with pytest.raises(ValueError):
        ConvergenceAdaptiveScheduler(metric_weights={"W2": -1.0})
    with pytest.raises(ValueError):
        ConvergenceAdaptiveScheduler(metric_weights={})


def test_convergence_adaptive_sample_audit_codes() -> None:
    """P0-A1: the adaptive family reports its shift in ``audit_codes``."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4)
    )
    codes = scheduler.sample(0, 0, 0).audit_codes
    assert codes[0] == "schedule_convergence_adaptive"
    assert codes[1].startswith("schedule_shift_applied:")
    for r, w2 in enumerate(_W2_TRACE[:3]):
        scheduler.record_round_feedback(r, {"W2": w2, "coverage": 0.5})
    codes = scheduler.sample(0, 1, 1).audit_codes
    assert "schedule_feedback_multi_metric:W2,coverage" in codes


# ---------------------------------------------------------------------------
# Wave 31 - paper-quantity-aware PID branch
# ---------------------------------------------------------------------------


_PAPER_QUANTITY_TRACE = (
    {"sheet_A": 0.7, "packing_B": 0.3, "exterior_gap": 0.1},
    {"sheet_A": 0.8, "packing_B": 0.2, "exterior_gap": 0.1},
    {"sheet_A": 0.9, "packing_B": 0.1, "exterior_gap": 0.1},
    {"sheet_A": 0.95, "packing_B": 0.05, "exterior_gap": 0.1},
)


def test_convergence_adaptive_paper_quantity_default_disabled() -> None:
    """Wave 31: a fresh scheduler is in the legacy W2-only branch."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=6)
    )
    assert scheduler.paper_quantity_enabled is False
    assert scheduler.smoothed_sheet_A is None
    assert scheduler.smoothed_packing_B is None
    assert scheduler.smoothed_exterior_gap is None
    assert scheduler.paper_ratio_history == ()
    assert scheduler.last_paper_quantity_keys == ()


def test_convergence_adaptive_paper_quantity_emas_track_samples() -> None:
    """Wave 31: ``record_round_feedback`` updates paper-quantity EMAs.

    With ``ema=0.5`` and the monotonic sheet_A trace, the EMA recursion
    is ``new = 0.5*sample + 0.5*prev``:
      round 0: 0.7
      round 1: 0.5*0.8 + 0.5*0.7 = 0.75
      round 2: 0.5*0.9 + 0.5*0.75 = 0.825
      round 3: 0.5*0.95 + 0.5*0.825 = 0.8875
    """
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=6),
        ema=0.5,
    )
    for r, pq in enumerate(_PAPER_QUANTITY_TRACE):
        scheduler.record_round_feedback(r, {"W2": 0.5}, paper_quantities=pq)
    assert scheduler.paper_quantity_enabled is True
    assert scheduler.smoothed_sheet_A == pytest.approx(0.8875)
    # packing_B shrinks: round 3 EMA = 0.5*0.05 + 0.5*0.175 = 0.1125.
    assert scheduler.smoothed_packing_B == pytest.approx(0.1125)
    assert scheduler.smoothed_exterior_gap == pytest.approx(0.1)
    assert scheduler.last_paper_quantity_keys == (
        "exterior_gap",
        "packing_B",
        "sheet_A",
    )


def test_convergence_adaptive_paper_quantity_ratio_formula() -> None:
    """Wave 31: PID uses ``sheet_A_ema / (sheet_A_ema + packing_B_ema)``.

    With ``ema=1.0`` (no smoothing: EMA = latest sample), the
    paper-quantity ratio tracks the literal ``sheet_A / (sheet_A +
    packing_B)`` formula.
    """
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=8),
        kp=0.30,
        kd=0.10,
        shift_max=0.5,
        ema=1.0,
    )
    for r, pq in enumerate(_PAPER_QUANTITY_TRACE):
        scheduler.record_round_feedback(r, {"W2": 0.5}, paper_quantities=pq)
    expected_ratios = (0.7, 0.8, 0.9, 0.95)
    assert scheduler.paper_ratio_history == pytest.approx(expected_ratios)
    # Ratio climbs monotonically; (1 - ratio) shrinks; the shift trends
    # negative (more exploration) because the sheet-vs-cell share grows.
    assert scheduler.shift < 0.0


def test_convergence_adaptive_legacy_w2_branch_unchanged_without_paper_quantities() -> None:
    """Wave 31: backward-compat - no paper quantities -> identical legacy path."""
    base = default_cosine_scheduler(cycle_length=8)
    scheduler = ConvergenceAdaptiveScheduler(
        base=base,
        metric_weights={"W2": 1.0},
    )
    for r, w2 in enumerate(_W2_TRACE):
        scheduler.record_round_feedback(r, {"W2": w2})
    assert scheduler.paper_quantity_enabled is False
    assert scheduler.smoothed_sheet_A is None
    assert scheduler.paper_ratio_history == ()
    assert scheduler.last_paper_quantity_keys == ()
    assert scheduler.smoothed_w2 is not None
    s0 = _W2_TRACE[0]
    s1 = 0.3 * _W2_TRACE[1] + 0.7 * s0
    s2 = 0.3 * _W2_TRACE[2] + 0.7 * s1
    s3 = 0.3 * _W2_TRACE[3] + 0.7 * s2
    s4 = 0.3 * _W2_TRACE[4] + 0.7 * s3
    assert scheduler.w2_history == pytest.approx((s0, s1, s2, s3, s4))


def test_convergence_adaptive_paper_quantity_ignores_broken_samples() -> None:
    """Wave 31: non-finite / negative paper-quantity samples are ignored."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=6),
        ema=0.3,
    )
    scheduler.record_round_feedback(
        0,
        {"W2": 0.5},
        paper_quantities={
            "sheet_A": float("nan"),
            "packing_B": float("inf"),
            "exterior_gap": -0.1,
        },
    )
    assert scheduler.smoothed_sheet_A is None
    assert scheduler.smoothed_packing_B is None
    assert scheduler.smoothed_exterior_gap is None
    assert scheduler.paper_ratio_history == ()
    assert scheduler.paper_quantity_enabled is False
    scheduler.record_round_feedback(
        1,
        {"W2": 0.5},
        paper_quantities={"sheet_A": 0.6, "packing_B": 0.4},
    )
    assert scheduler.smoothed_sheet_A == pytest.approx(0.6)
    assert scheduler.smoothed_packing_B == pytest.approx(0.4)
    assert scheduler.paper_ratio_history == (0.6,)
    assert scheduler.paper_quantity_enabled is True


def test_convergence_adaptive_paper_quantity_weights_round_trip() -> None:
    """Wave 31: paper_quantity_weights survive ``to_config`` / ``from_config``."""
    custom = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4),
        paper_quantity_weights={
            "sheet_A": 2.0,
            "packing_B": 0.5,
            "exterior_gap": 0.0,
        },
    )
    rebuilt = ConvergenceAdaptiveScheduler.from_config(custom.to_config())
    assert rebuilt.paper_quantity_weights == {
        "sheet_A": 2.0,
        "packing_B": 0.5,
        "exterior_gap": 0.0,
    }
    assert rebuilt.config_hash() == custom.config_hash()
    default_sched = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4)
    )
    assert "paper_quantity_weights" not in default_sched.to_config()
    legacy_like = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4)
    )
    assert default_sched.config_hash() == legacy_like.config_hash()


def test_convergence_adaptive_rejects_bad_paper_quantity_weights() -> None:
    """Wave 31: negative / empty paper-quantity weight maps are rejected."""
    with pytest.raises(ValueError):
        ConvergenceAdaptiveScheduler(paper_quantity_weights={"sheet_A": -1.0})
    with pytest.raises(ValueError):
        ConvergenceAdaptiveScheduler(paper_quantity_weights={})


def test_convergence_adaptive_paper_quantity_reset_clears_state() -> None:
    """Wave 31: ``reset()`` clears paper-quantity EMA + ratio history."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=6),
        ema=0.3,
    )
    for r, pq in enumerate(_PAPER_QUANTITY_TRACE):
        scheduler.record_round_feedback(r, {"W2": 0.5}, paper_quantities=pq)
    assert scheduler.paper_quantity_enabled is True
    assert scheduler.paper_ratio_history != ()
    scheduler.reset()
    assert scheduler.smoothed_sheet_A is None
    assert scheduler.smoothed_packing_B is None
    assert scheduler.smoothed_exterior_gap is None
    assert scheduler.paper_ratio_history == ()
    assert scheduler.last_paper_quantity_keys == ()
    assert scheduler.paper_quantity_enabled is False
    assert scheduler.w2_history == ()
    assert scheduler.smoothed_w2 is None


def test_convergence_adaptive_sample_audit_codes_paper_quantity() -> None:
    """Wave 31: paper-quantity-aware mode appears in ``audit_codes``."""
    scheduler = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=6)
    )
    for r, pq in enumerate(_PAPER_QUANTITY_TRACE[:2]):
        scheduler.record_round_feedback(r, {"W2": 0.5}, paper_quantities=pq)
    codes = scheduler.sample(0, 2, 2).audit_codes
    assert (
        "schedule_paper_quantity_enabled:exterior_gap,packing_B,sheet_A"
        in codes
    )


# ---------------------------------------------------------------------------
# Wave 95 Phase 1.D — shift_max default widen (0.15 → 0.30)
# ---------------------------------------------------------------------------


def test_shift_max_default_is_030() -> None:
    """The default ``shift_max`` on both adaptive schedulers is 0.30.

    Wave 95 Phase 1.D widen: pre-Wave-95 the default was 0.15, which
    clipped legitimate PID corrections on rounds whose per-cell
    sheet-evidence ratio dipped below ~0.7 (the canonical operating
    point for framework-armed framework-vs-baseline eval). Bumping to
    0.30 doubles the dynamic range without changing the call shape,
    so this is a pure behaviour-widen, no API surface change.
    """
    convergence = ConvergenceAdaptiveScheduler()
    assert convergence.shift_max == pytest.approx(0.30), (
        f"ConvergenceAdaptiveScheduler default shift_max is "
        f"{convergence.shift_max!r}; expected 0.30 (Wave 95 widen)."
    )
    paper_ratio = PaperRatioAdaptiveScheduler()
    assert paper_ratio.shift_max == pytest.approx(0.30), (
        f"PaperRatioAdaptiveScheduler default shift_max is "
        f"{paper_ratio.shift_max!r}; expected 0.30 (Wave 95 widen)."
    )


# ---------------------------------------------------------------------------
# Cross-reference: CodimensionSheetScheduler is still used in some
# ConvergenceAdaptive code paths. Kept here so the import remains linked
# (the helper file at module load time does not otherwise reference
# CodimensionSheetScheduler).
# ---------------------------------------------------------------------------


_ = CodimensionSheetScheduler  # noqa: F841  (keep import live)
