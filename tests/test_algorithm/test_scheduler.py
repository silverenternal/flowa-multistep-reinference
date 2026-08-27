"""Tests for the abstract algorithm layer (SchedulerProtocol + cosine default)."""

from __future__ import annotations

import math
import warnings
from itertools import pairwise

import pytest

from adaptive_reflow.algorithm import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SchedulerProtocol,
    ScheduleSample,
    SigmoidScheduler,
    build_scheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler import _paper_evidence_balance
from adaptive_reflow.schedule.cosine import CosineScheduleSampler


def _legacy_sampler(config) -> CosineScheduleSampler:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return CosineScheduleSampler(config)


def test_scheduler_protocol_runtime_checkable() -> None:
    scheduler = default_cosine_scheduler()
    assert isinstance(scheduler, SchedulerProtocol)
    assert isinstance(scheduler, CosineAnnealScheduler)


def test_cosine_anneal_scheduler_matches_legacy() -> None:
    scheduler = default_cosine_scheduler(cycle_length=8, n_min=0.1, n_max=0.9)
    legacy = _legacy_sampler(scheduler.config)
    for r in range(8):
        new = scheduler.sample(0, r, r)
        old = legacy.sample(0, r, r)
        assert new.n_cap == pytest.approx(float(old.n_cap))
        assert new.u_r == pytest.approx(old.u_r)
        assert new.family == old.family
        assert new.cycle_length == old.cycle_length
        assert new.memory_fraction() == pytest.approx(1.0 - float(old.n_cap))


def test_scheduler_sample_is_pure() -> None:
    scheduler = default_cosine_scheduler(cycle_length=5)
    a = scheduler.sample(2, 3, 7)
    b = scheduler.sample(2, 3, 7)
    assert a == b
    assert isinstance(a, ScheduleSample)


def test_scheduler_config_hash_is_stable() -> None:
    a = default_cosine_scheduler(cycle_length=12, n_min=0.2, n_max=0.8)
    b = default_cosine_scheduler(cycle_length=12, n_min=0.2, n_max=0.8)
    assert a.config_hash() == b.config_hash()
    a.sample(0, 1, 1)
    assert a.config_hash() == b.config_hash()
    c = default_cosine_scheduler(cycle_length=13, n_min=0.2, n_max=0.8)
    assert c.config_hash() != a.config_hash()


def test_scheduler_reset_clears_state() -> None:
    scheduler = default_cosine_scheduler(cycle_length=4)
    assert scheduler.last_sample is None
    scheduler.sample(0, 1, 1)
    assert scheduler.last_sample is not None
    scheduler.reset()
    assert scheduler.last_sample is None


def test_scheduler_accessors() -> None:
    scheduler = default_cosine_scheduler(cycle_length=6)
    assert scheduler.cycle_length() == 6
    assert scheduler.schedule_family() == "cosine_no_restart"


def test_legacy_sampler_emits_deprecation_warning() -> None:
    config = default_cosine_scheduler().config
    with pytest.warns(DeprecationWarning):
        CosineScheduleSampler(config)


# ---------------------------------------------------------------------------
# ConstantScheduler
# ---------------------------------------------------------------------------


def test_constant_scheduler_n_cap_is_constant() -> None:
    """ConstantScheduler must emit the same n_cap for every round."""
    scheduler = ConstantScheduler(cycle_length=10, n_cap=0.5)
    samples = [scheduler.sample(0, r, r) for r in range(10)]
    n_caps = {s.n_cap for s in samples}
    assert n_caps == {0.5}
    assert scheduler.schedule_family() == "constant"
    assert scheduler.cycle_length() == 10
    assert all(s.family == "constant" for s in samples)
    assert all(s.u_r == 0.5 for s in samples)


# ---------------------------------------------------------------------------
# LinearScheduler
# ---------------------------------------------------------------------------


def test_linear_scheduler_n_cap_ramps_monotonically() -> None:
    """LinearScheduler must produce a monotonic (decreasing) ramp n_min -> n_max."""
    scheduler = LinearScheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    samples = [scheduler.sample(0, r, r) for r in range(10)]
    n_caps = [s.n_cap for s in samples]
    # Closed form n_max - (n_max - n_min) * u_r with n_max > n_min
    # produces a strictly decreasing sequence.
    for prev, curr in pairwise(n_caps):
        assert curr < prev
    assert n_caps[0] == pytest.approx(1.0)  # round 0 -> n_max
    assert n_caps[-1] == pytest.approx(0.0)  # round L-1 -> n_min
    assert scheduler.schedule_family() == "linear"


# ---------------------------------------------------------------------------
# ExponentialScheduler
# ---------------------------------------------------------------------------


def test_exponential_scheduler_n_cap_decays() -> None:
    """ExponentialScheduler must produce a strictly non-increasing n_cap sequence."""
    scheduler = ExponentialScheduler(cycle_length=10, n_max=1.0, alpha=0.2)
    samples = [scheduler.sample(0, r, r) for r in range(10)]
    n_caps = [s.n_cap for s in samples]
    # Strictly decreasing for alpha > 0.
    for prev, curr in pairwise(n_caps):
        assert curr < prev
    # Closed form check at round 1: n_max * exp(-alpha * 1).
    assert n_caps[1] == pytest.approx(math.exp(-0.2))
    assert scheduler.schedule_family() == "exponential"


# ---------------------------------------------------------------------------
# Registry + factory
# ---------------------------------------------------------------------------


def test_build_scheduler_factory_dispatches_by_family() -> None:
    """build_scheduler must return the right class for each registered family."""
    assert isinstance(build_scheduler("cosine"), CosineAnnealScheduler)
    assert isinstance(build_scheduler("constant"), ConstantScheduler)
    assert isinstance(build_scheduler("linear"), LinearScheduler)
    assert isinstance(build_scheduler("exponential"), ExponentialScheduler)
    assert isinstance(build_scheduler("polynomial"), PolynomialScheduler)
    assert isinstance(build_scheduler("sigmoid"), SigmoidScheduler)
    # Whitespace + case tolerance.
    assert isinstance(build_scheduler("  COSINE  "), CosineAnnealScheduler)
    # Unknown family -> KeyError.
    with pytest.raises(KeyError):
        build_scheduler("not_a_family")


# ---------------------------------------------------------------------------
# PolynomialScheduler
# ---------------------------------------------------------------------------


def test_polynomial_scheduler_power_1_is_linear() -> None:
    """PolynomialScheduler(power=1) must equal LinearScheduler at each round."""
    cycle_length = 11
    poly = PolynomialScheduler(
        cycle_length=cycle_length, n_min=0.0, n_max=1.0, power=1.0
    )
    linear = LinearScheduler(cycle_length=cycle_length, n_min=0.0, n_max=1.0)
    for r in range(cycle_length):
        p = poly.sample(0, r, r)
        ln = linear.sample(0, r, r)
        assert p.n_cap == pytest.approx(ln.n_cap)
        assert p.u_r == pytest.approx(ln.u_r)


def test_polynomial_scheduler_concave_with_power_2() -> None:
    """power=2 gives a concave-style ramp between linear and cosine.

    Closed forms at u_r=0.5 (with n_min=0.2, n_max=0.8):
    - Linear:   n_cap = n_max - (n_max - n_min) * 0.5 = 0.5
    - Cosine:   n_cap = n_min + (n_max - n_min) * (1 + cos(pi*0.5)) / 2 = 0.5
    - Polynomial (power=2): n_cap = n_min + (n_max - n_min) * (1 - 0.25) = 0.65

    The polynomial(power=2) lands *above* the (degenerate-equal) linear
    and cosine midpoints — its closed form keeps capacity higher for
    longer before catching up at the endpoints.
    """
    n_min, n_max = 0.2, 0.8
    cycle_length = 21  # midpoint round = 10, u_r = 0.5
    poly = PolynomialScheduler(
        cycle_length=cycle_length, n_min=n_min, n_max=n_max, power=2.0
    )
    linear = LinearScheduler(cycle_length=cycle_length, n_min=n_min, n_max=n_max)
    cosine = default_cosine_scheduler(
        cycle_length=cycle_length, n_min=n_min, n_max=n_max
    )
    midpoint_round = (cycle_length - 1) // 2
    p = poly.sample(0, midpoint_round, midpoint_round)
    ln = linear.sample(0, midpoint_round, midpoint_round)
    co = cosine.sample(0, midpoint_round, midpoint_round)
    linear_val = float(ln.n_cap)
    cosine_val = float(co.n_cap)
    poly_val = float(p.n_cap)
    # Endpoints must match linear/cosine exactly (closed-form agreement).
    assert p.n_cap > linear_val
    assert p.n_cap > cosine_val
    expected_poly = n_min + (n_max - n_min) * 0.75
    assert poly_val == pytest.approx(expected_poly)
    # Sanity: linear and cosine are equal at u_r=0.5 by symmetry.
    assert linear_val == pytest.approx(cosine_val)


def test_polynomial_scheduler_power_zero_raises() -> None:
    """PolynomialScheduler rejects power <= 0 with a ValueError."""
    with pytest.raises(ValueError):
        PolynomialScheduler(cycle_length=4, power=0.0)
    with pytest.raises(ValueError):
        PolynomialScheduler(cycle_length=4, power=-1.0)


def test_polynomial_scheduler_clips_n_cap() -> None:
    """PolynomialScheduler defensively clips n_cap into [0, 1]."""
    # Huge power produces extreme values; clip must hold the result.
    scheduler = PolynomialScheduler(
        cycle_length=3, n_min=0.0, n_max=1.0, power=20.0
    )
    for r in range(3):
        sample = scheduler.sample(0, r, r)
        assert 0.0 <= sample.n_cap <= 1.0


def test_polynomial_scheduler_config_hash_varies_with_power() -> None:
    """PolynomialScheduler config_hash must differ across power values."""
    a = PolynomialScheduler(cycle_length=5, power=1.0)
    b = PolynomialScheduler(cycle_length=5, power=2.0)
    c = PolynomialScheduler(cycle_length=5, power=3.0)
    assert a.config_hash() != b.config_hash()
    assert b.config_hash() != c.config_hash()
    # Same parameters -> same hash.
    a2 = PolynomialScheduler(cycle_length=5, power=1.0)
    assert a.config_hash() == a2.config_hash()


def test_polynomial_scheduler_byte_deterministic_under_repeated_reset() -> None:
    """Repeated reset + sample must yield byte-identical samples."""
    scheduler = PolynomialScheduler(
        cycle_length=8, n_min=0.1, n_max=0.9, power=3.5
    )
    n_caps_first = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    # Reset and re-sample; values must match exactly (byte-for-byte equal
    # floats — Python float equality is exact when bits match).
    scheduler.reset()
    n_caps_second = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    assert n_caps_first == n_caps_second
    # Repeated iteration without reset must also be stable.
    n_caps_third = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    assert n_caps_first == n_caps_third


# ---------------------------------------------------------------------------
# SigmoidScheduler
# ---------------------------------------------------------------------------


def test_sigmoid_scheduler_symmetric_midpoint_0_5() -> None:
    """At u_r=0.5 with midpoint=0.5, sigmoid(0)=0.5, so n_cap=(n_min+n_max)/2."""
    n_min, n_max = 0.2, 0.8
    cycle_length = 21
    scheduler = SigmoidScheduler(
        cycle_length=cycle_length,
        n_min=n_min,
        n_max=n_max,
        steepness=10.0,
        midpoint=0.5,
    )
    midpoint_round = (cycle_length - 1) // 2
    sample = scheduler.sample(0, midpoint_round, midpoint_round)
    expected = 0.5 * (n_min + n_max)
    assert sample.n_cap == pytest.approx(expected)
    assert sample.u_r == pytest.approx(0.5)


def test_sigmoid_scheduler_steepness_zero_is_constant() -> None:
    """steepness=0 makes sigmoid(0)=0.5, so n_cap=(n_min+n_max)/2 for all rounds."""
    n_min, n_max = 0.2, 0.8
    cycle_length = 11
    scheduler = SigmoidScheduler(
        cycle_length=cycle_length,
        n_min=n_min,
        n_max=n_max,
        steepness=0.0,
        midpoint=0.5,
    )
    expected = 0.5 * (n_min + n_max)
    for r in range(cycle_length):
        s = scheduler.sample(0, r, r)
        assert s.n_cap == pytest.approx(expected)


def test_sigmoid_scheduler_low_steepness_is_smooth() -> None:
    """With low steepness the n_cap curve is gradual — adjacent rounds differ little."""
    cycle_length = 11
    scheduler = SigmoidScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        steepness=2.0,
        midpoint=0.5,
    )
    n_caps = [scheduler.sample(0, r, r).n_cap for r in range(cycle_length)]
    # Adjacent-step deltas stay small.
    deltas = [abs(n_caps[r + 1] - n_caps[r]) for r in range(cycle_length - 1)]
    assert max(deltas) < 0.5
    # The curve is monotonically increasing (steepness > 0, n_max > n_min).
    for prev, curr in pairwise(n_caps):
        assert curr >= prev - 1e-12


def test_sigmoid_scheduler_high_steepness_is_step() -> None:
    """With high steepness the n_cap curve is near-step at the midpoint."""
    cycle_length = 11
    scheduler = SigmoidScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        steepness=50.0,
        midpoint=0.5,
    )
    midpoint_round = (cycle_length - 1) // 2
    samples = [scheduler.sample(0, r, r).n_cap for r in range(cycle_length)]
    # Rounds before the midpoint sit near n_min; rounds after the midpoint
    # sit near n_max. The midpoint round itself is exactly 0.5.
    first_half_max = max(samples[:midpoint_round])
    second_half = samples[midpoint_round + 1:]
    second_half_min = min(second_half)
    assert first_half_max < 0.1
    assert second_half_min > 0.9
    # The midpoint itself is exactly the centred value.
    assert samples[midpoint_round] == pytest.approx(0.5)


def test_sigmoid_scheduler_config_hash_includes_steepness_and_midpoint() -> None:
    """SigmoidScheduler config_hash must change with steepness and midpoint."""
    a = SigmoidScheduler(cycle_length=5, steepness=10.0, midpoint=0.5)
    b = SigmoidScheduler(cycle_length=5, steepness=20.0, midpoint=0.5)
    c = SigmoidScheduler(cycle_length=5, steepness=10.0, midpoint=0.7)
    d = SigmoidScheduler(cycle_length=5, steepness=10.0, midpoint=0.5)
    assert a.config_hash() != b.config_hash()
    assert a.config_hash() != c.config_hash()
    assert a.config_hash() == d.config_hash()


def test_sigmoid_scheduler_byte_deterministic_under_repeated_reset() -> None:
    """Repeated reset + sample must yield byte-identical samples."""
    scheduler = SigmoidScheduler(
        cycle_length=8,
        n_min=0.1,
        n_max=0.9,
        steepness=8.0,
        midpoint=0.5,
    )
    n_caps_first = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    scheduler.reset()
    n_caps_second = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    assert n_caps_first == n_caps_second
    n_caps_third = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    assert n_caps_first == n_caps_third


# ---------------------------------------------------------------------------
# Registry dispatch for new scheduler types
# ---------------------------------------------------------------------------


def test_build_scheduler_dispatches_polynomial_and_sigmoid() -> None:
    """build_scheduler must return Polynomial/Sigmoid for the new families."""
    poly = build_scheduler("polynomial")
    assert isinstance(poly, PolynomialScheduler)
    assert poly.schedule_family() == "polynomial"
    assert poly.cycle_length() == 20  # default

    sig = build_scheduler("sigmoid")
    assert isinstance(sig, SigmoidScheduler)
    assert sig.schedule_family() == "sigmoid"
    assert sig.cycle_length() == 20  # default

    # Defaults can be overridden via kwargs.
    poly2 = build_scheduler(
        "polynomial", cycle_length=5, n_min=0.1, n_max=0.9, power=3.0
    )
    assert isinstance(poly2, PolynomialScheduler)
    assert poly2.cycle_length() == 5
    assert poly2.power == 3.0


# ---------------------------------------------------------------------------
# Protocol conformance for every registered scheduler
# ---------------------------------------------------------------------------


def test_all_schedulers_conform_to_protocol() -> None:
    """Every registered scheduler class must satisfy SchedulerProtocol structurally."""
    assert set(SCHEDULER_REGISTRY) == {
        "codimension_sheet",
        "cosine",
        "constant",
        "linear",
        "exponential",
        "polynomial",
        "sigmoid",
        "convergence_adaptive",
    }
    instances: list[SchedulerProtocol] = [
        default_cosine_scheduler(cycle_length=5),
        ConstantScheduler(cycle_length=5),
        LinearScheduler(cycle_length=5),
        ExponentialScheduler(cycle_length=5),
        PolynomialScheduler(cycle_length=5),
        SigmoidScheduler(cycle_length=5),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=5),
    ]
    for instance in instances:
        assert isinstance(instance, SchedulerProtocol)
        # Every Protocol method must be callable and return the right shape.
        sample = instance.sample(0, 0, 0)
        assert isinstance(sample, ScheduleSample)
        assert isinstance(instance.cycle_length(), int)
        assert isinstance(instance.schedule_family(), str)
        assert isinstance(instance.config_hash(), str)
        instance.reset()


# ---------------------------------------------------------------------------
# ConvergenceAdaptiveScheduler
# ---------------------------------------------------------------------------


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
    """When W2 improves (delta<0, ratio<1), the shift trends positive."""
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
    assert scheduler.w2_history == (1.0, 0.5)
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
    scheduler = build_scheduler("convergence_adaptive")
    assert isinstance(scheduler, ConvergenceAdaptiveScheduler)
    assert scheduler.schedule_family() == "convergence_adaptive_cosine"
    # And the registry key is normalised case- and whitespace-insensitively.
    scheduler = build_scheduler("  CONVERGENCE_ADAPTIVE  ")
    assert isinstance(scheduler, ConvergenceAdaptiveScheduler)


# ---------------------------------------------------------------------------
# Default feedback hook on every registered scheduler
# ---------------------------------------------------------------------------


def test_all_schedulers_have_noop_record_round_feedback() -> None:
    """Every scheduler exposes a callable record_round_feedback (no-op by default)."""
    schedulers = [
        default_cosine_scheduler(cycle_length=5),
        ConstantScheduler(cycle_length=5),
        LinearScheduler(cycle_length=5),
        ExponentialScheduler(cycle_length=5),
        PolynomialScheduler(cycle_length=5),
        SigmoidScheduler(cycle_length=5),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=5),
    ]
    for s in schedulers:
        assert hasattr(s, "record_round_feedback")
        assert callable(s.record_round_feedback)
        # The default no-op returns None and mutates no state.
        assert s.record_round_feedback(0, {"W2": 1.0}) is None
        # Resetting still works after a feedback call.
        s.reset()


# ---------------------------------------------------------------------------
# CodimensionSheetScheduler — paper Theorem 1 / Lemmas 2 + 3
# ---------------------------------------------------------------------------


def _noop_profile(x: float) -> float:
    """Identity-free residual profile for codimension-scheduler tests."""
    return float(x)


def test_paper_evidence_balance_helper_closed_form() -> None:
    """_paper_evidence_balance matches the closed form in the ADR."""
    eps = 0.1
    for n_base in (0.0, 0.25, 0.5, 0.75, 1.0):
        sheet = 1.0 / max(n_base, eps)
        cell = (1.0 - n_base) ** 2 / (eps * eps)
        expected = sheet / (sheet + cell)
        got = _paper_evidence_balance(n_base, eps)
        assert got == pytest.approx(expected, rel=1e-12)


def test_paper_evidence_balance_helper_rejects_invalid_eps() -> None:
    """The helper refuses non-finite or non-positive eps_implicit."""
    with pytest.raises(ValueError, match="finite"):
        _paper_evidence_balance(0.5, float("nan"))
    with pytest.raises(ValueError, match="eps_implicit"):
        _paper_evidence_balance(0.5, 0.0)
    with pytest.raises(ValueError, match="eps_implicit"):
        _paper_evidence_balance(0.5, -0.01)


def test_codimension_sheet_scheduler_high_eps_stays_close_to_cosine() -> None:
    """At eps_implicit=1.0 the codim scheduler tracks the base cosine shape.

    With eps=1.0 the formula maps ``n_cap_base in [0, 1]`` to
    ``n_cap_out in [0.5, 1.0]`` (the formula's natural range at that
    scale). The codim output is monotonic in the base schedule's
    ``n_cap_base`` so the two schedules produce samples that correlate
    round-by-round (within a bounded offset).
    """
    base = default_cosine_scheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    codim = CodimensionSheetScheduler(
        cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=1.0
    )
    base_caps = [base.sample(0, r, r).n_cap for r in range(10)]
    codim_caps = [codim.sample(0, r, r).n_cap for r in range(10)]
    # Both are monotonic-decreasing in r for the cosine family; the codim
    # scheduler must preserve the same monotonic direction at eps=1.0.
    for b_prev, b_curr, c_prev, c_curr in zip(
        base_caps[:-1], base_caps[1:], codim_caps[:-1], codim_caps[1:],
        strict=True,
    ):
        if b_curr > b_prev:
            assert c_curr >= c_prev
    # Codim output stays within the formula's natural range at eps=1.0
    # ([0.5, 1.0] for n_min=0, n_max=1).
    for n in codim_caps:
        assert 0.5 - 1e-9 <= n <= 1.0 + 1e-9
    # Round-by-round the codim scheduler tracks the base within a
    # bounded offset; worst case is r=0 (base=0 -> codim=0.5).
    for b, c in zip(base_caps, codim_caps, strict=True):
        assert abs(c - b) < 0.6


def test_codimension_sheet_scheduler_low_eps_amplifies_selection() -> None:
    """At eps_implicit=0.01 the codim scheduler compresses n_cap toward n_min.

    With a small eps the cell-evidence term dominates the denominator
    at every non-trivial base n_cap, so the ratio collapses toward 0
    and n_cap_out sits near n_min (closed-form paper Lemma 3 bound
    realised). The mid-cycle output must therefore be much smaller
    than the same round's base cosine n_cap.
    """
    base = default_cosine_scheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    codim = CodimensionSheetScheduler(
        cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.01
    )
    base_mid = base.sample(0, 5, 5).n_cap
    codim_mid = codim.sample(0, 5, 5).n_cap
    # The cosine baseline at the midpoint is well above 0.4.
    assert base_mid > 0.4
    # And the codim scheduler compresses it strongly toward n_min.
    assert codim_mid < 0.05
    # The low-eps compression holds across the cycle: in every round
    # where the base cosine is non-trivial, the codim scheduler output
    # is at most 0.2 (the r=0 special case is exempt because base=1
    # makes cell evidence vanish entirely there).
    small_compression_count = 0
    for r in range(10):
        c = codim.sample(0, r, r).n_cap
        if r != 0:
            assert c < 0.2
            small_compression_count += 1
    assert small_compression_count >= 8


def test_codimension_sheet_scheduler_handles_degenerate_base() -> None:
    """When the base cosine emits 0 (cycle terminal round), n_cap ~ n_min.

    With ``n_cap_base=0`` the closed form is
    ``ratio = 1 / (1 + 1/eps_implicit)``. For ``eps_implicit=0.05``
    that is ``1/21 ~= 0.0476`` and the n_cap output is 0.0476 -- small
    but not identically 0 (the formula's degenerate case has nonzero
    sheet evidence).
    """
    codim = CodimensionSheetScheduler(
        cycle_length=4, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    # r=3 is the cycle terminal round; the cosine base with n_min=0
    # emits exactly 0.0 at this slot.
    sample = codim.sample(0, 3, 3)
    assert sample.n_cap == pytest.approx(1.0 / 21.0, abs=1e-9)
    # The helper matches.
    expected_ratio = _paper_evidence_balance(0.0, 0.05)
    assert expected_ratio == pytest.approx(1.0 / 21.0, abs=1e-9)
    # And with a large enough n_min + larger eps the degeneracy is
    # squarely in cell-evidence territory.
    big_codim = CodimensionSheetScheduler(
        cycle_length=2, n_min=0.5, n_max=1.0, eps_implicit=1.0
    )
    # n_cap_base = 0 at r=1; sheet=1/1=1, cell=1/1=1, ratio=0.5.
    sample = big_codim.sample(0, 1, 1)
    assert sample.n_cap == pytest.approx(0.75, abs=1e-9)


def test_codimension_sheet_scheduler_is_byte_deterministic() -> None:
    """Two CodimensionSheetScheduler instances with identical kwargs agree."""
    kwargs = dict(
        cycle_length=12,
        n_min=0.1,
        n_max=0.9,
        profile_residual_fn=_noop_profile,
        eps_implicit=0.07,
        seed=42,
    )
    a = CodimensionSheetScheduler(**kwargs)
    b = CodimensionSheetScheduler(**kwargs)
    for r in range(12):
        sa = a.sample(0, r, r)
        sb = b.sample(0, r, r)
        assert sa.n_cap == pytest.approx(sb.n_cap)
        assert sa.u_r == pytest.approx(sb.u_r)
        assert sa.family == sb.family == "codimension_sheet"
        assert sa.schedule_hash == sb.schedule_hash
        assert sa.memory_fraction() == pytest.approx(sb.memory_fraction())


def test_codimension_sheet_scheduler_config_hash_includes_eps_implicit_and_profile_signature() -> None:
    """The config_hash captures both eps_implicit and profile identity."""
    base_kwargs = dict(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=None,
        seed=0,
    )
    h0 = CodimensionSheetScheduler(**base_kwargs).config_hash()
    # Vary eps_implicit.
    h_lo = CodimensionSheetScheduler(
        **{**base_kwargs, "eps_implicit": 0.01}
    ).config_hash()
    h_hi = CodimensionSheetScheduler(
        **{**base_kwargs, "eps_implicit": 0.07}
    ).config_hash()
    assert h_lo != h0
    assert h_hi != h0
    assert h_lo != h_hi
    # Vary the profile callable.
    h_prof = CodimensionSheetScheduler(
        **{**base_kwargs, "profile_residual_fn": _noop_profile}
    ).config_hash()
    assert h_prof != h0
    # Same callable -> same hash (signature is qualname-derived).
    h_prof_again = CodimensionSheetScheduler(
        **{**base_kwargs, "profile_residual_fn": _noop_profile}
    ).config_hash()
    assert h_prof == h_prof_again
    # The profile_signature accessor exposes the same identifier string.
    scheduler = CodimensionSheetScheduler(
        **{**base_kwargs, "profile_residual_fn": _noop_profile}
    )
    assert scheduler.profile_signature.endswith("_noop_profile")
    # And a None profile yields the canonical "default_sheet" signature.
    none_scheduler = CodimensionSheetScheduler(**base_kwargs)
    assert none_scheduler.profile_signature == "default_sheet"


def test_codimension_sheet_scheduler_clip_in_unit_interval() -> None:
    """n_cap stays in [n_min, n_max] (and therefore in [0, 1]) for every round."""
    codim = CodimensionSheetScheduler(
        cycle_length=20, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    for r in range(20):
        sample = codim.sample(0, r, r)
        assert 0.0 <= sample.n_cap <= 1.0
        # And via the canonical memory-fraction transform.
        assert 0.0 <= sample.memory_fraction() <= 1.0
    # Even with extreme eps (the closed form keeps the ratio in [0, 1]).
    extreme_low = CodimensionSheetScheduler(cycle_length=10, eps_implicit=1e-12)
    extreme_high = CodimensionSheetScheduler(cycle_length=10, eps_implicit=1e6)
    for r in range(10):
        s_lo = extreme_low.sample(0, r, r)
        s_hi = extreme_high.sample(0, r, r)
        assert 0.0 <= s_lo.n_cap <= 1.0
        assert 0.0 <= s_hi.n_cap <= 1.0


def test_codimension_sheet_scheduler_build_scheduler_factory() -> None:
    """build_scheduler('codimension_sheet') returns the codim class."""
    scheduler = build_scheduler(
        "codimension_sheet",
        cycle_length=8,
        eps_implicit=0.05,
    )
    assert isinstance(scheduler, CodimensionSheetScheduler)
    assert scheduler.schedule_family() == "codimension_sheet"
    # And the registry is case- and whitespace-insensitive.
    scheduler = build_scheduler("  CODIMENSION_SHEET  ", cycle_length=8)
    assert isinstance(scheduler, CodimensionSheetScheduler)
    # profile_residual_fn passes through the factory.
    scheduler = build_scheduler(
        "codimension_sheet",
        cycle_length=8,
        eps_implicit=0.05,
        profile_residual_fn=_noop_profile,
    )
    assert scheduler.profile_signature.endswith("_noop_profile")
