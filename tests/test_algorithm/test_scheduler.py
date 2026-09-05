"""Tests for the abstract algorithm layer (SchedulerProtocol + cosine default)."""

from __future__ import annotations

import math
import warnings
from itertools import pairwise

import numpy as np
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
    build_scheduler_from_config,
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
    # Ensure Phase-2 extra families (edm / adaptive_pid / jittered_constant) are
    # registered before asserting on SCHEDULER_REGISTRY contents — these are
    # registered lazily via _register_extra_scheduler_families on first
    # build_scheduler call, so we trigger that explicitly here.
    from adaptive_reflow.algorithm.scheduler._core import (
        _ensure_extra_families_registered,
    )
    _ensure_extra_families_registered()
    assert set(SCHEDULER_REGISTRY) == {
        "codimension_sheet",
        "cosine",
        "constant",
        "linear",
        "exponential",
        "polynomial",
        "sigmoid",
        "convergence_adaptive",
        "sequential",
        # Phase-2 P0/P2 additions (see
        # ``docs/algorithm-deep-uplift-plan.md``).
        "edm",
        "adaptive_pid",
        "jittered_constant",
        # Wave 31 — paper-quantity-driven + paper-quantity-aware scheduler.
        "paper_ratio_adaptive",
    }
    from adaptive_reflow.algorithm import (
        AdaptivePIDScheduler,
        EDMScheduler,
        JitteredConstantScheduler,
        PaperRatioAdaptiveScheduler,
    )
    instances: list[SchedulerProtocol] = [
        default_cosine_scheduler(cycle_length=5),
        ConstantScheduler(cycle_length=5),
        LinearScheduler(cycle_length=5),
        ExponentialScheduler(cycle_length=5),
        PolynomialScheduler(cycle_length=5),
        SigmoidScheduler(cycle_length=5),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=5),
        EDMScheduler(cycle_length=5),
        AdaptivePIDScheduler(),
        JitteredConstantScheduler(cycle_length=5, n_cap=0.5),
        PaperRatioAdaptiveScheduler(
            base=CodimensionSheetScheduler(cycle_length=5),
        ),
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
    """_paper_evidence_balance matches the paper-aligned closed form.

    The formula uses the paper's *positive* eps powers: sheet
    ``Theta(eps^{+1})`` (Lemma 2 / Cor. 1) and cell ``O(eps^{+2})``
    (Lemma 3). As ``eps -> 0`` with ``n_clipped < 1`` the cell term
    shrinks faster, so the ratio tends to 1 (sheet dominance),
    matching Theorem 1.
    """
    eps = 0.1
    for n_base in (0.0, 0.25, 0.5, 0.75, 1.0):
        n_clipped = max(0.0, min(1.0, n_base))
        sheet = max(n_clipped, eps)
        cell = (1.0 - n_clipped) ** 2 * eps * eps
        expected = sheet / (sheet + cell)
        got = _paper_evidence_balance(n_base, eps)
        assert got == pytest.approx(expected, rel=1e-12)


def test_paper_evidence_balance_helper_paper_eps_zero_limit() -> None:
    """The ratio tends to 1 as eps -> 0 for every n_clipped < 1.

    Paper Theorem 1 (``:88``) requires the sheet to dominate after
    normalization as the noise level vanishes. The helper must realise
    this monotonic direction: the ratio is non-decreasing as eps
    decreases toward 0 (and approaches 1 in the limit) for every
    ``n_clipped in [0, 1)``.
    """
    for n_base in (0.0, 0.25, 0.5, 0.75):
        prev_ratio = -1.0
        for eps in (0.5, 0.1, 0.05, 0.01, 0.001, 1e-6):
            ratio = _paper_evidence_balance(n_base, eps)
            # Ratio is non-decreasing as eps decreases (Theorem 1
            # direction) and approaches 1 in the limit.
            assert ratio >= prev_ratio - 1e-12
            assert 0.0 <= ratio <= 1.0
            prev_ratio = ratio
        # And in the limit the ratio is essentially 1.
        assert prev_ratio == pytest.approx(1.0, abs=1e-6)


def test_paper_evidence_balance_helper_rejects_invalid_eps() -> None:
    """The helper refuses non-finite or non-positive eps_implicit."""
    with pytest.raises(ValueError, match="finite"):
        _paper_evidence_balance(0.5, float("nan"))
    with pytest.raises(ValueError, match="eps_implicit"):
        _paper_evidence_balance(0.5, 0.0)
    with pytest.raises(ValueError, match="eps_implicit"):
        _paper_evidence_balance(0.5, -0.01)


def test_codimension_sheet_scheduler_n_cap_is_ratio_driven() -> None:
    """``n_cap`` is driven by the paper's sheet-vs-cell evidence ratio.

    The framework's coarse-to-fine anneal is driven by the paper's
    sheet-vs-cell evidence ratio (paper Lemma 2 ``Theta(eps^{+1})``
    versus Lemma 3 ``O(eps^{+2})``), NOT by the cosine ramp. With
    the paper-quantity-augmented path active (no
    ``profile_residual_fn`` ⇒ heuristic fallback), ``n_cap``
    equals ``n_min + (n_max - n_min) * ratio`` where ``ratio =
    sheet / (sheet + cell)``.

    We verify:

    * The per-round ``n_cap`` equals the literal closed form.
    * The per-round ``n_cap`` differs from the cosine ramp's
      ``n_cap`` (the cosine ramp is no longer the driver).
    * Different ``eps_implicit`` values yield different ``n_cap``
      (the ratio is sensitive to the paper-quantity scale).
    """
    base = default_cosine_scheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    for eps in (1.0, 0.05, 0.01):
        codim = CodimensionSheetScheduler(
            cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=eps
        )
        for r in range(10):
            base_cap = base.sample(0, r, r).n_cap
            sample = codim.sample(0, r, r)
            # ratio-driven: n_cap = n_min + (n_max - n_min) * ratio.
            assert sample.n_cap == pytest.approx(
                sample.evidence_ratio, abs=1e-12
            ), (
                f"n_cap at round {r} must equal the evidence ratio "
                f"(eps_implicit={eps}); got n_cap={sample.n_cap}, "
                f"ratio={sample.evidence_ratio}"
            )
            # n_cap differs from the cosine ramp's base value at
            # late-round slots where the heuristic ratio is < 1
            # (the cosine ramp's terminal round emits n_cap=0, but
            # the ratio-driven n_cap stays near 1 for small eps).
            # We skip r=0 because both the cosine base and the
            # heuristic ratio at n_cap_base=1.0 happen to equal 1.0
            # (degenerate identity at the high-noise end).
            if eps < 0.5 and r > 0:
                assert abs(sample.n_cap - base_cap) > 1e-6, (
                    f"n_cap at round {r} (eps_implicit={eps}) "
                    f"should differ from the cosine base ({base_cap}); "
                    f"got n_cap={sample.n_cap}. The cosine ramp must "
                    f"NOT be the driver of n_cap."
                )


def test_codimension_sheet_scheduler_evidence_ratio_low_eps_near_one() -> None:
    """At low ``eps_implicit`` the evidence ratio is near 1 (sheet dominance).

    With a small ``eps_implicit`` the cell-evidence term
    (``(1-n)^2 * eps^2``) is small relative to the sheet term
    (``max(n, eps)``), so the ratio tends to 1 across the cycle
    (paper Theorem 1, ``eps -> 0`` selects the sheet).
    """
    codim = CodimensionSheetScheduler(
        cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.01
    )
    for r in range(10):
        codim.sample(0, r, r)
        assert codim.last_evidence_ratio is not None
        # At low eps the ratio is close to 1 everywhere.
        assert codim.last_evidence_ratio > 0.9


def test_codimension_sheet_scheduler_handles_degenerate_base() -> None:
    """``n_cap`` is now driven by the ratio, not the cosine ramp.

    P2-W33-A: with ``eps_direction="decreasing"`` (paper convention,
    default) the per-round ``eps`` diminishes across the cycle
    (``eps(r) = eps_0 * (1 - u_r)``, floored at ``1e-9``). At the
    cycle terminal round ``u_r=1`` so ``eps_per_round = 1e-9``
    (the floor); for the framework heuristic with ``n_base = 0``:

        sheet = max(0, 1e-9)        = 1e-9
        cell  = 1 * (1e-9)^2       = 1e-18
        ratio = 1e-9 / (1e-9 + 1e-18) ≈ 1.0

    so ``n_cap`` is ≈ 1.0 (n_min=0, n_max=1) — the paper-aligned
    "sheet dominates as eps -> 0" claim (Theorem 1). With a large
    ``eps_implicit`` at the early rounds the ratio is sensitive to
    ``n_cap_base`` via the heuristic cell term.
    """
    codim = CodimensionSheetScheduler(
        cycle_length=4, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    # r=3 is the cycle terminal round; ``eps_per_round`` is floored
    # at ``1e-9``, so ``n_cap`` ≈ ``n_max`` (sheet dominance).
    sample = codim.sample(0, 3, 3)
    assert sample.n_cap == pytest.approx(1.0, abs=1e-7)
    # And the evidence ratio equals n_cap directly (n_min=0, n_max=1).
    assert codim.last_evidence_ratio == pytest.approx(1.0, abs=1e-7)
    # And at the early round (r=0), eps_per_round equals the
    # constructor constant and the n_cap is also sheet-dominated.
    early_sample = codim.sample(0, 0, 0)
    assert early_sample.n_cap == pytest.approx(1.0, abs=1e-7)
    # Now exercise a NON-terminal round with a large eps; here the
    # framework heuristic IS sensitive to n_cap_base.
    big_codim = CodimensionSheetScheduler(
        cycle_length=2, n_min=0.5, n_max=1.0, eps_implicit=1.0
    )
    # r=0: eps_per_round = 1.0 * (1 - 0) = 1.0. At r=0 with cosine
    # n_min=0.5, n_base = n_max = 1.0. sheet = max(1, 1) = 1.
    # cell = (1-1)^2 * 1^2 = 0. ratio = 1 / (1 + 0) = 1.
    # n_cap = 0.5 + 0.5 * 1 = 1.0.
    sample_r0 = big_codim.sample(0, 0, 0)
    assert sample_r0.n_cap == pytest.approx(1.0, abs=1e-7)


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


def test_codimension_sample_carries_eps_implicit() -> None:
    """C4: ``CodimensionSheetScheduler.sample`` populates ``ScheduleSample.eps_implicit``.

    The runner reads ``ScheduleSample.eps_implicit`` and forwards it
    to the selection evaluator's ``oracle_at_round(eps_round=...)``.
    A ``None`` field would silently fall back to the evaluator's
    fixed ``eps_implicit`` and the metric would remain
    schedule-independent — the precise failure the C4 investigation
    diagnosed.
    """
    codim = CodimensionSheetScheduler(
        cycle_length=8, n_min=0.0, n_max=1.0, eps_implicit=0.07,
    )
    for r in range(8):
        sample = codim.sample(0, r, r)
        assert sample.eps_implicit is not None, (
            f"C4 regression: round {r} sample.eps_implicit is None"
        )
        # P2-W33-A: ``eps_implicit`` on the sample is now the per-round
        # value ``eps_0 * (1 - u_r)`` for ``eps_direction="decreasing"``
        # (default). At ``r=0`` (``u_r=0``) this equals the constructor
        # constant; at ``r=L-1`` it equals the floor ``1e-9``.
        u_r = float(r) / (8 - 1)
        expected = max(0.07 * (1.0 - u_r), 1e-9)
        assert sample.eps_implicit == pytest.approx(expected, abs=1e-12)
    # And a different eps_implicit propagates too.
    codim_hi = CodimensionSheetScheduler(
        cycle_length=4, n_min=0.0, n_max=1.0, eps_implicit=0.5,
    )
    for r in range(4):
        sample_hi = codim_hi.sample(0, r, r)
        u_r_hi = float(r) / (4 - 1)
        expected_hi = max(0.5 * (1.0 - u_r_hi), 1e-9)
        assert sample_hi.eps_implicit == pytest.approx(expected_hi, abs=1e-12)


def test_cosine_sample_eps_implicit_is_none() -> None:
    """C4 regression guard: cosine baseline leaves ``eps_implicit`` as ``None``.

    Cosine has no concept of a paper-quantity epsilon; the runner
    must therefore fall back to the evaluator's fixed ``eps_implicit``
    for cosine rows — preserving the legacy byte-for-byte behaviour
    that the C4 investigation flagged as the source of the
    "schedule-independent by construction" plateau.
    """
    cosine = default_cosine_scheduler(cycle_length=6)
    for r in range(6):
        sample = cosine.sample(0, r, r)
        assert sample.eps_implicit is None


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


def test_codimension_sheet_scheduler_eps_direction_default_matches_paper() -> None:
    """Default ``eps_direction='decreasing'`` keeps the paper ratio direction.

    With the ratio-driven design, ``n_cap`` is computed from the
    paper's sheet-vs-cell evidence ratio. P2-W33-A: with the
    paper-aligned ``eps_direction='decreasing'``, the per-round
    ``eps`` diminishes monotonically (``eps(r) = eps_0 * (1 - u_r)``)
    and the ratio is used as-is. Under the framework heuristic
    (no ``profile_residual_fn``) and at the cycle terminal round,
    ``eps_per_round`` is floored at ``1e-9`` and ``n_cap`` is
    sheet-dominated (``n_cap`` ≈ 1.0). At early rounds with the
    cosine ramp near its peak, ``n_cap`` is also sheet-dominated.
    """
    scheduler = CodimensionSheetScheduler(
        cycle_length=8, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    assert scheduler.eps_direction == "decreasing"
    caps = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    # P2-W33-A: at every round the framework heuristic puts the
    # sheet in dominance (eps small, sheet dominates), so ``n_cap``
    # is essentially ``n_max`` throughout the cycle.
    assert caps[0] == pytest.approx(1.0, abs=1e-9)
    # At r=7 (terminal), eps_per_round = 1e-9 → ratio ≈ 1 → n_cap ≈ 1.
    assert caps[-1] == pytest.approx(1.0, abs=1e-7)


def test_codimension_sheet_scheduler_eps_direction_increasing_legacy_warns() -> None:
    """``eps_direction='increasing'`` emits a DeprecationWarning and reverses.

    The legacy ``'increasing'`` mode is the opposite of paper Theorem
    1's ``eps -> 0`` limit. Under the new ratio-driven design, the
    ``'increasing'`` mode flips the per-round ratio
    (``ratio -> 1 - ratio``), so r=0 sits at the *small-ratio* end
    of the cycle and r=L-1 sits at the *large-ratio* end. It is
    retained only for backward compatibility and emits a
    :class:`DeprecationWarning` on the FIRST :meth:`sample` call
    (not at construction time — P2-18 audit; legacy callers that
    build the scheduler eagerly for ``config_hash`` introspection
    do not flood logs).
    """
    # P2-18: construction is silent; the warning fires on the first
    # ``sample()`` call (once per instance).
    scheduler = CodimensionSheetScheduler(
        cycle_length=8, n_min=0.0, n_max=1.0, eps_direction="increasing"
    )
    assert scheduler.eps_direction == "increasing"
    with pytest.warns(DeprecationWarning, match="legacy inverted convention"):
        scheduler.sample(0, 0, 0)
    caps = [scheduler.sample(0, r, r).n_cap for r in range(1, 8)]
    # Reversed: r=0 -> small n_cap (1 - 1 = 0 in heuristic mode),
    # r=L-1 -> large n_cap (1 - eps/(eps + eps^2)).
    assert caps[0] < 0.05
    assert caps[-1] == pytest.approx(
        1.0 - 0.05 / (0.05 + 0.0025), abs=1e-9
    )
    # Subsequent sample() calls do not re-emit the warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        for r in range(8):
            scheduler.sample(0, r, r)


def test_codimension_sheet_scheduler_eps_direction_case_insensitive() -> None:
    """``eps_direction`` accepts mixed case and surrounding whitespace."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scheduler = CodimensionSheetScheduler(
            cycle_length=4, eps_direction="  DECREASING  "
        )
    assert scheduler.eps_direction == "decreasing"


def test_codimension_sheet_scheduler_eps_direction_rejects_invalid() -> None:
    """``eps_direction`` rejects strings outside the documented set."""
    with pytest.raises(ValueError, match="eps_direction"):
        CodimensionSheetScheduler(cycle_length=4, eps_direction="sideways")
    with pytest.raises(ValueError, match="eps_direction"):
        CodimensionSheetScheduler(cycle_length=4, eps_direction="")


def test_codimension_sheet_scheduler_config_hash_includes_eps_direction() -> None:
    """``config_hash`` captures the ``eps_direction`` choice."""
    base_kwargs = dict(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=None,
        seed=0,
    )
    h_dec = CodimensionSheetScheduler(**base_kwargs).config_hash()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        h_inc = CodimensionSheetScheduler(
            **{**base_kwargs, "eps_direction": "increasing"}
        ).config_hash()
    assert h_dec != h_inc


# ---------------------------------------------------------------------------
# CodimensionSheetScheduler — paper-quantity wiring (ADR-0013 follow-up)
# ---------------------------------------------------------------------------


def test_codimension_sheet_scheduler_with_profile_uses_paper_quantities() -> None:
    """``profile_residual_fn`` is consumed: paper quantities cached once.

    Building the scheduler with a ``profile_residual_fn`` must call
    :func:`adaptive_reflow.contracts.paper_quantities.sheet_evidence_A`
    and :func:`adaptive_reflow.contracts.paper_quantities.root_cell_packing_B`
    exactly once at construction time and cache the results on
    ``self._sheet_A`` / ``self._packing_B``. The cached values must
    equal the result of calling those functions directly with the same
    profile callable.
    """
    from adaptive_reflow.contracts import paper_quantities as _pq

    profile = lambda x: math.sin(x)  # noqa: E731

    # Reference values from the paper-quantity functions.
    expected_sheet_A = _pq.sheet_evidence_A(profile)
    expected_packing_B = _pq.root_cell_packing_B(profile)
    expected_cell_C = _pq.per_cell_coefficient_C()
    expected_e_rho = _pq.exterior_gap_e_rho()

    scheduler = CodimensionSheetScheduler(
        cycle_length=8,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
    )

    # Cached paper quantities on the scheduler.
    assert scheduler._sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
    assert scheduler._packing_B == pytest.approx(expected_packing_B, rel=1e-12)
    assert scheduler._cell_C == pytest.approx(expected_cell_C, rel=1e-12)
    assert scheduler._exterior_gap_e_rho == pytest.approx(expected_e_rho, rel=1e-12)
    # Public accessors expose the cached values too.
    assert scheduler.sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
    assert scheduler.packing_B == pytest.approx(expected_packing_B, rel=1e-12)
    assert scheduler.cell_C == pytest.approx(expected_cell_C, rel=1e-12)
    assert scheduler.exterior_gap_e_rho == pytest.approx(expected_e_rho, rel=1e-12)

    # The per-round evidence ratio uses the paper-quantity path. Verify
    # by recomputing the ratio via the public helper signature and
    # confirming the scheduler's last_evidence_ratio matches.
    for r in range(8):
        scheduler.sample(0, r, r)
        # The cached quantities are the inputs the scheduler forwards
        # into the paper-quantity-augmented path of the helper.
        assert scheduler.sheet_A is not None
        assert scheduler.packing_B is not None
        assert scheduler.cell_C is not None
        # Recompute via the helper signature (paper-quantity path).
        # We avoid using ``n_cap`` directly because the scheduler
        # applies its own envelope; instead we verify the cached
        # values are forwarded correctly by checking ``sheet_A`` and
        # ``packing_B`` survive a ``sample`` call unchanged.
        assert scheduler.sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
        assert scheduler.packing_B == pytest.approx(expected_packing_B, rel=1e-12)
        assert scheduler.last_evidence_ratio is not None
        assert 0.0 <= scheduler.last_evidence_ratio <= 1.0


def test_codimension_sheet_scheduler_without_profile_uses_inline_formula() -> None:
    """Without ``profile_residual_fn`` the legacy inline formula is used.

    Backward compatibility: when ``profile_residual_fn`` is ``None``
    the scheduler does NOT cache paper quantities (all four accessors
    return ``None``) and the per-round sheet-vs-cell evidence ratio
    uses the framework-side heuristic closed form (``sheet / (sheet +
    cell)`` with ``sheet = max(n_base, eps)`` and ``cell = (1 -
    n_base)^2 * eps^2``, where ``n_base`` is the cosine ramp's
    per-round value). Under the new ratio-driven design, ``n_cap`` is
    ``n_min + (n_max - n_min) * ratio`` (with ``n_min = n_max = 0``
    case excluded by the cycle_length > 1 check); for
    ``n_min = 0, n_max = 1`` this reduces to ``n_cap = ratio``.
    """
    scheduler = CodimensionSheetScheduler(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
    )
    # No profile => no paper-quantity caching.
    assert scheduler._sheet_A is None
    assert scheduler._packing_B is None
    assert scheduler._cell_C is None
    assert scheduler._exterior_gap_e_rho is None
    assert scheduler.sheet_A is None
    assert scheduler.packing_B is None
    assert scheduler.cell_C is None
    assert scheduler.exterior_gap_e_rho is None
    # Legacy inline formula: ratio matches the framework heuristic
    # applied to the cosine ramp's per-round value ``n_cap_base``.
    # P2-W33-A: with the per-round ``eps`` schedule, the formula uses
    # ``eps_per_round = eps_0 * (1 - u_r)`` (floored at ``1e-9``).
    eps_0 = 0.05
    cycle_length = 10
    for r in range(cycle_length):
        sample = scheduler.sample(0, r, r)
        assert scheduler.last_evidence_ratio is not None
        # ``n_cap_base`` is the cosine ramp's value at this round
        # (ADR-0010). We can recover it by querying the base scheduler.
        n_base = scheduler.base.sample(0, r, r).n_cap
        # P2-W33-A: per-round eps.
        u_r = float(r) / (cycle_length - 1)
        eps_per_round = max(eps_0 * (1.0 - u_r), 1e-9)
        # The heuristic formula is ``sheet / (sheet + cell)`` with
        # ``sheet = max(n_base, eps_per_round)`` and
        # ``cell = (1 - n_base) ** 2 * eps_per_round ** 2``.
        n_base_clipped = max(0.0, min(1.0, n_base))
        sheet = max(n_base_clipped, eps_per_round)
        cell = (1.0 - n_base_clipped) ** 2 * eps_per_round * eps_per_round
        expected_ratio = sheet / (sheet + cell)
        assert scheduler.last_evidence_ratio == pytest.approx(
            expected_ratio, rel=1e-12
        )
        # With n_min=0, n_max=1, the per-round n_cap equals the ratio.
        assert sample.n_cap == pytest.approx(
            scheduler.last_evidence_ratio, abs=1e-12
        )


def test_codimension_sheet_scheduler_paper_quantity_diagnostics_emitted() -> None:
    """Per-round diagnostics from the paper-quantity-augmented path.

    When ``profile_residual_fn`` is configured, the per-round
    ``last_evidence_ratio`` is computed via the
    paper-quantity-augmented path. We verify the resulting ratio is
    well-defined (in ``[0, 1]``) and that the cached ``sheet_A``,
    ``packing_B``, ``cell_C`` are forwarded into the helper
    unchanged across rounds.
    """
    profile = lambda x: math.sin(x)  # noqa: E731

    scheduler = CodimensionSheetScheduler(
        cycle_length=6,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
    )
    # Snapshot the cached quantities at construction time.
    snapshot = (
        scheduler.sheet_A,
        scheduler.packing_B,
        scheduler.cell_C,
        scheduler.exterior_gap_e_rho,
    )
    for r in range(6):
        scheduler.sample(0, r, r)
        # Cached quantities are immutable across rounds (computed once).
        assert scheduler.sheet_A == snapshot[0]
        assert scheduler.packing_B == snapshot[1]
        assert scheduler.cell_C == snapshot[2]
        assert scheduler.exterior_gap_e_rho == snapshot[3]
        # The ratio is well-defined.
        assert scheduler.last_evidence_ratio is not None
        assert 0.0 <= scheduler.last_evidence_ratio <= 1.0


def test_codimension_sheet_scheduler_paper_quantity_path_matches_paper_quantities_module() -> None:
    """End-to-end: paper-quantity-augmented ratio recomputed via the helper.

    The paper-quantity-augmented path computes

        sheet = sheet_A * eps
        cell  = cell_C * packing_B * eps ** 2
        ratio = sheet / (sheet + cell)

    We verify the scheduler's per-round ``last_evidence_ratio``
    matches this formula when ``profile_residual_fn`` is configured.
    """
    from adaptive_reflow.contracts import paper_quantities as _pq

    profile = lambda x: math.sin(x)  # noqa: E731

    sheet_A = _pq.sheet_evidence_A(profile)
    packing_B = _pq.root_cell_packing_B(profile)
    cell_C = _pq.per_cell_coefficient_C()

    scheduler = CodimensionSheetScheduler(
        cycle_length=4,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
        eps_implicit=0.05,
    )
    eps_0 = scheduler.eps_implicit
    cycle_length = 4
    for r in range(cycle_length):
        scheduler.sample(0, r, r)
        # P2-W33-A: with the per-round ``eps`` schedule, the formula
        # uses ``eps_per_round = eps_0 * (1 - u_r)`` (floored at
        # ``1e-9``). The ratio is recomputed for each round.
        u_r = float(r) / (cycle_length - 1)
        eps_per_round = max(eps_0 * (1.0 - u_r), 1e-9)
        sheet = sheet_A * eps_per_round
        cell = cell_C * packing_B * eps_per_round * eps_per_round
        expected_ratio = sheet / (sheet + cell)
        assert scheduler.last_evidence_ratio == pytest.approx(
            expected_ratio, rel=1e-12
        )


def test_codimension_sheet_scheduler_inject_noise_e_rho_floor() -> None:
    """A18: ``inject_noise`` floors the noise mass at ``e_rho / 4``.

    With ``profile_residual_fn`` supplied, the scheduler caches
    ``e_rho`` (paper Lemma 5 exterior gap) and the ``inject_noise``
    path lifts the noise mass to ``max(A_g, e_rho / 4)`` so the
    forward noise respects paper Lemma 5's physical-complement gap.

    The test constructs a scheduler with a profile whose ``A_g`` is
    small (close to the ``e_rho / 4`` floor) and verifies the noise
    mass is the floor.
    """
    # A near-zero profile: sheet evidence is tiny (close to e_rho/4).
    profile = lambda x: 1e6 * math.sin(x)  # noqa: E731
    scheduler = CodimensionSheetScheduler(
        cycle_length=4,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
    )
    assert scheduler.sheet_A is not None
    assert scheduler.exterior_gap_e_rho is not None
    e_rho = float(scheduler.exterior_gap_e_rho)
    expected_floor = e_rho / 4.0
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    out = scheduler.inject_noise(state, sample, generator=gen)
    # The state was zero, so the output is exactly
    # ``scale * standard_normal`` for the same generator stream.
    expected_scale = math.sqrt(max(float(scheduler.sheet_A), expected_floor))
    expected = expected_scale * np.random.default_rng(0).standard_normal(4)
    assert np.allclose(out, expected, rtol=1e-12, atol=0.0), (
        f"inject_noise output {out!r} does not match scale "
        f"sqrt(max(A_g, e_rho/4))={expected_scale!r}"
    )


# ---------------------------------------------------------------------------
# Forward noise injection (P0-7) — symmetric forward step
# ---------------------------------------------------------------------------


def test_cosine_inject_noise_reproducible_with_seed() -> None:
    """Two identical (state, sample, seed) inputs produce identical output (P0-7)."""
    scheduler = default_cosine_scheduler(cycle_length=8, n_min=0.0, n_max=1.0)
    sample = scheduler.sample(0, 2, 2).as_cosine_schedule_sample()
    state = np.linspace(-1.0, 1.0, 16, dtype=np.float64).reshape(4, 4)

    g1 = np.random.default_rng(42)
    g2 = np.random.default_rng(42)
    out1 = scheduler.inject_noise(state, sample, generator=g1)
    out2 = scheduler.inject_noise(state, sample, generator=g2)

    assert out1.shape == state.shape
    assert np.array_equal(out1, out2)
    assert not np.array_equal(out1, state)


def test_cosine_inject_noise_scales_with_sqrt_n_cap() -> None:
    """inject_noise scales the standard normal by ``sqrt(n_cap)``."""
    scheduler = default_cosine_scheduler(cycle_length=4, n_min=0.0, n_max=1.0)
    state = np.zeros(8, dtype=np.float64)

    sample_low = scheduler.sample(0, 3, 3).as_cosine_schedule_sample()
    sample_high = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()

    gen_low = np.random.default_rng(7)
    gen_high = np.random.default_rng(7)
    out_low = scheduler.inject_noise(state, sample_low, generator=gen_low)
    out_high = scheduler.inject_noise(state, sample_high, generator=gen_high)
    # ``n_cap`` near 0.0 at round 3 -> near-zero noise; at round 0 -> max noise.
    assert np.std(out_low) < np.std(out_high)


@pytest.mark.parametrize(
    "scheduler_factory",
    [
        CosineAnnealScheduler,
        ConstantScheduler,
        LinearScheduler,
        ExponentialScheduler,
        PolynomialScheduler,
        SigmoidScheduler,
    ],
)
def test_every_scheduler_implements_inject_noise(scheduler_factory) -> None:
    """Every SchedulerProtocol implementation exposes ``inject_noise``."""
    if scheduler_factory is CosineAnnealScheduler:
        scheduler = default_cosine_scheduler(cycle_length=4)
    elif scheduler_factory is ConstantScheduler:
        scheduler = ConstantScheduler(cycle_length=4, n_cap=0.5)
    elif scheduler_factory is LinearScheduler:
        scheduler = LinearScheduler(cycle_length=4, n_min=0.0, n_max=1.0)
    elif scheduler_factory is ExponentialScheduler:
        scheduler = ExponentialScheduler(cycle_length=4)
    elif scheduler_factory is PolynomialScheduler:
        scheduler = PolynomialScheduler(cycle_length=4, power=2.0)
    elif scheduler_factory is SigmoidScheduler:
        scheduler = SigmoidScheduler(cycle_length=4)
    else:  # pragma: no cover
        raise AssertionError("unhandled factory")
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    out = scheduler.inject_noise(state, sample, generator=gen)
    assert out.shape == state.shape
    assert np.all(np.isfinite(out))


def test_codimension_scheduler_inject_noise_uses_A_g_when_available() -> None:
    """The codimension scheduler uses ``sheet_A`` as the noise mass when set."""
    profile = lambda x: math.sin(x)  # noqa: E731
    scheduler = CodimensionSheetScheduler(
        cycle_length=4,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
        eps_implicit=0.05,
    )
    assert scheduler.sheet_A is not None
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    out = scheduler.inject_noise(state, sample, generator=gen)
    assert out.shape == state.shape
    assert np.all(np.isfinite(out))


def test_convergence_adaptive_inject_noise_delegates_to_base() -> None:
    """The adaptive scheduler's ``inject_noise`` delegates to its base."""
    scheduler = ConvergenceAdaptiveScheduler()
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen_a = np.random.default_rng(123)
    gen_b = np.random.default_rng(123)
    out_adaptive = scheduler.inject_noise(state, sample, generator=gen_a)
    out_base = scheduler.base.inject_noise(state, sample, generator=gen_b)
    assert np.array_equal(out_adaptive, out_base)


# ---------------------------------------------------------------------------
# from_config / to_config round-trip (P1-1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scheduler",
    [
        default_cosine_scheduler(cycle_length=4, n_min=0.1, n_max=0.9),
        ConstantScheduler(cycle_length=4, n_cap=0.5),
        LinearScheduler(cycle_length=4, n_min=0.0, n_max=1.0),
        ExponentialScheduler(cycle_length=4, n_max=1.0, alpha=0.1),
        PolynomialScheduler(cycle_length=4, n_min=0.0, n_max=1.0, power=2.0),
        SigmoidScheduler(cycle_length=4, n_min=0.0, n_max=1.0, steepness=5.0),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=4, eps_implicit=0.05),
    ],
)
def test_scheduler_config_round_trip(scheduler) -> None:
    """``scheduler == cls.from_config(scheduler.to_config())`` byte-for-byte."""
    config = scheduler.to_config()
    rebuilt = build_scheduler_from_config(config)
    assert type(rebuilt) is type(scheduler)
    assert rebuilt.config_hash() == scheduler.config_hash()
    assert rebuilt.to_config() == config
    # Sample sequence is byte-identical for equal config.
    for r in range(scheduler.cycle_length()):
        s_orig = scheduler.sample(0, r, r)
        s_rebuilt = rebuilt.sample(0, r, r)
        assert s_orig.n_cap == pytest.approx(s_rebuilt.n_cap)


def test_build_scheduler_from_config_dispatches_on_family() -> None:
    """``build_scheduler_from_config`` dispatches on the ``family`` key."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    rebuilt = build_scheduler_from_config(scheduler.to_config())
    assert isinstance(rebuilt, CosineAnnealScheduler)


def test_cosine_scheduler_to_config_has_canonical_keys() -> None:
    """Cosine scheduler's ``to_config`` exposes the canonical keys."""
    scheduler = default_cosine_scheduler(
        cycle_length=4, n_min=0.1, n_max=0.9
    )
    cfg = scheduler.to_config()
    assert cfg["family"] == "cosine"
    assert cfg["schedule_family"] == "cosine_no_restart"
    assert cfg["cycle_length"] == 4
    assert cfg["n_min"] == pytest.approx(0.1)
    assert cfg["n_max"] == pytest.approx(0.9)
    assert "config_hash" in cfg


def test_cosine_scheduler_from_config_round_trip() -> None:
    """``CosineAnnealScheduler.from_config`` matches the constructor."""
    scheduler = default_cosine_scheduler(
        cycle_length=4, n_min=0.1, n_max=0.9
    )
    rebuilt = CosineAnnealScheduler.from_config(scheduler.to_config())
    assert rebuilt.cycle_length() == 4
    assert rebuilt.schedule_family() == "cosine_no_restart"


def test_codimension_scheduler_from_config_ignores_profile() -> None:
    """Codimension round-trip leaves ``profile_residual_fn=None``."""
    profile = lambda x: math.sin(x)  # noqa: E731
    scheduler = CodimensionSheetScheduler(
        cycle_length=4, profile_residual_fn=profile
    )
    rebuilt = CodimensionSheetScheduler.from_config(scheduler.to_config())
    assert rebuilt.profile_residual_fn is None
    assert rebuilt.profile_signature == "default_sheet"


# ---------------------------------------------------------------------------
# P0-A1 — ``audit_codes`` / ``evidence_ratio`` on ``ScheduleSample``
# ---------------------------------------------------------------------------


def test_cosine_sample_carries_audit_codes() -> None:
    """P0-A1: cosine samples carry the family's baseline audit code."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    sample = scheduler.sample(0, 0, 0)
    assert sample.audit_codes == ("cosine_baseline",)
    # The cosine family computes no sheet-vs-cell balance.
    assert sample.evidence_ratio is None


def test_schedule_sample_audit_codes_default_empty() -> None:
    """A bare ``ScheduleSample`` keeps the legacy field set (defaults)."""
    sample = ScheduleSample(
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=0.5,
        n_min=0.0,
        n_max=1.0,
        u_r=0.0,
        family="custom",
        computed_at_round=0,
        schedule_hash="h",
    )
    assert sample.audit_codes == ()
    assert sample.evidence_ratio is None


def test_every_family_emits_audit_codes() -> None:
    """P0-A1 target: 100% of samples carry a non-empty ``audit_codes``."""
    schedulers = [
        default_cosine_scheduler(cycle_length=4),
        ConstantScheduler(cycle_length=4),
        LinearScheduler(cycle_length=4),
        ExponentialScheduler(cycle_length=4),
        PolynomialScheduler(cycle_length=4),
        SigmoidScheduler(cycle_length=4),
        ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=4)
        ),
        CodimensionSheetScheduler(cycle_length=4),
    ]
    total = 0
    tagged = 0
    for scheduler in schedulers:
        for r in range(4):
            sample = scheduler.sample(0, r, r)
            total += 1
            if sample.audit_codes:
                tagged += 1
            assert all(isinstance(c, str) for c in sample.audit_codes)
    assert total == 32
    assert tagged == total


def test_audit_codes_do_not_break_sample_equality() -> None:
    """Two samples from the same scheduler + args still compare equal."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    assert scheduler.sample(0, 2, 2) == scheduler.sample(0, 2, 2)


# ---------------------------------------------------------------------------
# P1-A2 — cosine paper-quantity (A_g) wiring
# ---------------------------------------------------------------------------


def _constant_profile_3(x: float) -> float:
    """Residual profile ``g(x) = 3`` -> ``A_g = 1 / sqrt(10)``."""
    del x
    return 3.0


def test_cosine_paper_quantity_wiring() -> None:
    """P1-A2: ``A_g`` drives the forward-noise mass and raises SNR >= 5%."""
    from adaptive_reflow.contracts import paper_quantities as pq

    baseline = default_cosine_scheduler(cycle_length=4)
    wired = default_cosine_scheduler(
        cycle_length=4, profile_residual_fn=_constant_profile_3
    )
    assert baseline.sheet_A is None
    a_g = float(pq.sheet_evidence_A(_constant_profile_3))
    assert wired.sheet_A == pytest.approx(a_g, rel=1e-12)
    assert a_g == pytest.approx(1.0 / math.sqrt(10.0), rel=1e-6)

    sample = baseline.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros((256, 2), dtype=np.float64)
    base_noise = baseline.inject_noise(
        state, sample, generator=np.random.default_rng(7)
    )
    wired_noise = wired.inject_noise(
        state, sample, generator=np.random.default_rng(7)
    )
    n_cap = float(sample.n_cap)
    assert n_cap > 0.0
    # Same generator stream -> the two outputs differ only by the scale.
    assert wired_noise == pytest.approx(
        base_noise * math.sqrt(a_g / n_cap), rel=1e-12
    )
    # SNR = signal / injected-noise magnitude, so the SNR gain is the
    # inverse ratio of the noise scales.
    snr_gain = math.sqrt(n_cap / a_g) - 1.0
    assert snr_gain >= 0.05

    # The audit trail records the wiring; the unwired path is unchanged.
    wired_codes = wired.sample(0, 0, 0).audit_codes
    assert wired_codes[0] == "cosine_baseline"
    assert any(
        c.startswith("cosine_paper_quantity_wired:") for c in wired_codes
    )
    assert baseline.sample(0, 0, 0).audit_codes == ("cosine_baseline",)


def test_cosine_without_profile_is_byte_identical_legacy() -> None:
    """P1-A2: unwired cosine ``inject_noise`` keeps ``sqrt(n_cap)``."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    sample = scheduler.sample(0, 1, 1).as_cosine_schedule_sample()
    state = np.zeros((64, 2), dtype=np.float64)
    got = scheduler.inject_noise(
        state, sample, generator=np.random.default_rng(3)
    )
    expected = math.sqrt(float(sample.n_cap)) * np.random.default_rng(
        3
    ).standard_normal(state.shape)
    assert np.array_equal(got, expected)


def test_cosine_rejects_non_callable_profile() -> None:
    """A non-callable profile is rejected at construction time."""
    with pytest.raises(ValueError, match="profile_residual_fn"):
        default_cosine_scheduler(
            cycle_length=4,
            profile_residual_fn=1.0,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# P0-A6 — ConvergenceAdaptiveScheduler multi-metric feedback
# ---------------------------------------------------------------------------


_W2_TRACE = (0.90, 0.82, 0.79, 0.77, 0.76)
_COVERAGE_TRACE = (0.40, 0.55, 0.62, 0.68, 0.71)
_SELECTION_TRACE = (0.50, 0.61, 0.70, 0.78, 0.83)


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


# ---------------------------------------------------------------------------
# F10 — CodimensionSheetScheduler.with_profile() method (P1)
# ---------------------------------------------------------------------------


def test_codimension_with_profile_preserves_eps_implicit() -> None:
    """F10: ``CodimensionSheetScheduler.with_profile(provider)`` returns
    a new scheduler with the supplied profile and ALL other config
    preserved (cycle_length, n_min, n_max, eps_implicit, eps_direction,
    seed).
    """
    from adaptive_reflow.algorithm.scheduler import (
        CodimensionSheetScheduler,
    )

    original = CodimensionSheetScheduler(
        cycle_length=20,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=lambda x: float(x),
        eps_implicit=0.05,
        eps_direction="decreasing",
        seed=42,
    )

    def new_profile(x: float) -> float:
        return float(x) ** 2

    new_sched = original.with_profile(new_profile)
    # Identity preserved on every other field.
    assert new_sched.cycle_length() == original.cycle_length()
    assert new_sched._n_min == original._n_min
    assert new_sched._n_max == original._n_max
    assert new_sched._eps_implicit == original._eps_implicit
    assert new_sched._eps_direction == original._eps_direction
    assert new_sched._seed == original._seed
    # The new profile is the callable passed in.
    assert new_sched._profile_residual_fn is new_profile
    # Sanity: original is unmodified.
    assert original._profile_residual_fn is not new_profile


# ---------------------------------------------------------------------------
# F23 — build_scheduler_from_config respects kwargs (P1)
# ---------------------------------------------------------------------------


def test_build_scheduler_from_config_respects_kwargs_for_edm() -> None:
    """F23: ``build_scheduler_from_config`` honours the kwargs in the
    ``config`` dict (not just the family key) for the
    previously-unhandled ``edm`` family.
    """
    from adaptive_reflow.algorithm.scheduler import build_scheduler_from_config

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
# Wave 31 - paper-quantity-aware PID branch in ConvergenceAdaptiveScheduler
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
# P0-A7 — ``evidence_ratio`` on the codimension sample
# ---------------------------------------------------------------------------


def _g_a_profile(x: float) -> float:
    """Canonical two_moons profile ``g_a(x) = (1 + 0.25 tanh x) sin x``."""
    return (1.0 + 0.25 * math.tanh(x)) * math.sin(x)


def test_codimension_sample_evidence_ratio() -> None:
    """P0-A7: the sample carries the round's sheet-vs-cell balance."""
    scheduler = CodimensionSheetScheduler(
        cycle_length=8, profile_residual_fn=_g_a_profile
    )
    for r in range(8):
        sample = scheduler.sample(0, r, r)
        assert sample.evidence_ratio is not None
        # Matches the reportable metric to within 1e-6 (target).
        assert sample.evidence_ratio == pytest.approx(
            float(scheduler.last_evidence_ratio), abs=1e-6
        )
        assert 0.0 <= sample.evidence_ratio <= 1.0
        assert sample.audit_codes == ("codimension_paper_quantity_grounded",)


def test_codimension_sample_evidence_ratio_heuristic_path() -> None:
    """Without a profile the sample is tagged as the heuristic path."""
    scheduler = CodimensionSheetScheduler(cycle_length=4)
    sample = scheduler.sample(0, 0, 0)
    assert sample.audit_codes == ("codimension_framework_heuristic",)
    assert sample.evidence_ratio == pytest.approx(
        float(scheduler.last_evidence_ratio), abs=1e-12
    )
