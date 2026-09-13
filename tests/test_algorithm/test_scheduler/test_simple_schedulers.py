"""Simple scheduler family tests (Constant / Linear / Exponential / Polynomial / Sigmoid).

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

import math
from itertools import pairwise

import pytest

from adaptive_reflow.algorithm import (
    ConstantScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SigmoidScheduler,
    build_scheduler,
    default_cosine_scheduler,
)

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
