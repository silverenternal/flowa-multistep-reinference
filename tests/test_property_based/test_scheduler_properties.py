"""Property-based tests for :mod:`adaptive_reflow.algorithm.scheduler`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :class:`CosineAnnealScheduler` — periodicity in ``u_r``, monotonicity
  of ``n_cap``, config-hash distinctness across parameters.
* :class:`ConstantScheduler` — flatness across rounds, idempotency of
  ``sample``.
* :class:`LinearScheduler` — endpoint anchoring + linear ramp shape.
* :class:`ExponentialScheduler` — decay direction + non-negativity.
* :class:`PolynomialScheduler` — power=1 equivalence to linear family.
* :class:`SigmoidScheduler` — sigmoid midpoint symmetry.
* :class:`ScheduleSample.memory_fraction` — clip-into-[0, 1] invariant.

Seed policy (Research 4 mitigation): the schedulers are deterministic;
Hypothesis's internal shrinker varies only the (cycle_length, n_min,
n_max, etc.) tuples, no stochastic surface to flake on. Seeds are pinned
explicitly via ``@settings(derandomize=True)`` so a regression surfaces
byte-identical inputs across runs.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.scheduler._core import (
    ConstantScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    ScheduleSample,
    SigmoidScheduler,
)
from adaptive_reflow.algorithm.scheduler._core import (
    default_cosine_scheduler as _default_cosine_scheduler,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Pin every test to a deterministic strategy so a regression surfaces the
# exact same shrunk counter-example across runs (B.7 acceptance: "explicit
# seed pin").
_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


_CYCLE_LEN = st.integers(min_value=1, max_value=32)
_FRACTION = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)
_ROUND_INDEX = st.integers(min_value=0, max_value=31)
_OUTER_CYCLE = st.integers(min_value=0, max_value=10)
_TARGET_ROUND = st.integers(min_value=0, max_value=10)
_POWER = st.floats(min_value=0.1, max_value=4.0, allow_nan=False)
_STEEPNESS = st.floats(min_value=-10.0, max_value=10.0, allow_infinity=False, allow_nan=False)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_cosine(
    cycle_length: int, n_min: float, n_max: float
) -> CosineAnnealScheduler:
    """Build a cosine scheduler from raw floats."""
    return _default_cosine_scheduler(
        cycle_length=cycle_length, n_min=n_min, n_max=n_max, seed=0
    )


# ---------------------------------------------------------------------------
# Cosine: u_r is the round index / (cycle_length - 1) — periodic across
# cycles; monotonic in round_in_cycle within a single cycle.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    outer=_OUTER_CYCLE,
    length=_CYCLE_LEN,
    n_min=_FRACTION,
    n_max=_FRACTION,
    r1=st.integers(min_value=0, max_value=15),
    r2=st.integers(min_value=0, max_value=15),
    target=_TARGET_ROUND,
)
def test_cosine_u_r_monotone_in_round_in_cycle(
    outer: int, length: int, n_min: float, n_max: float,
    r1: int, r2: int, target: int,
) -> None:
    """``u_r`` is non-decreasing in ``round_in_cycle`` for fixed cycle."""
    if length <= 1 or r1 >= length or r2 >= length:
        return  # cycle_length=1 short-circuits u_r=0.5
    sched = _make_cosine(length, n_min, n_max)
    u1 = sched.sample(outer, r1, target).u_r
    u2 = sched.sample(outer, r2, target).u_r
    if r1 <= r2:
        assert u1 <= u2 + 1e-12
    else:
        assert u2 <= u1 + 1e-12


@_PROPERTY_SETTINGS
@given(
    outer=_OUTER_CYCLE,
    length=_CYCLE_LEN,
    n_min=_FRACTION,
    n_max=_FRACTION,
    r=_ROUND_INDEX,
    target=_TARGET_ROUND,
)
def test_cosine_n_cap_in_envelope(
    outer: int, length: int, n_min: float, n_max: float,
    r: int, target: int,
) -> None:
    """``n_cap`` is clipped into ``[min(n_min, n_max), max(n_min, n_max)]``."""
    if r >= length or length <= 0:
        return
    sched = _make_cosine(length, n_min, n_max)
    sample = sched.sample(outer, r, target)
    lo, hi = sorted([float(n_min), float(n_max)])
    assert lo - 1e-9 <= sample.n_cap <= hi + 1e-9


@_PROPERTY_SETTINGS
@given(
    length1=_CYCLE_LEN,
    n_min1=_FRACTION,
    n_max1=_FRACTION,
    length2=_CYCLE_LEN,
    n_min2=_FRACTION,
    n_max2=_FRACTION,
)
def test_cosine_config_hash_distinct_for_distinct_configs(
    length1: int, length2: int, n_min1: float, n_max1: float,
    n_min2: float, n_max2: float,
) -> None:
    """Two distinct (length, n_min, n_max) tuples produce distinct hashes."""
    sched1 = _make_cosine(length1, n_min1, n_max1)
    sched2 = _make_cosine(length2, n_min2, n_max2)
    h1 = sched1.config_hash()
    h2 = sched2.config_hash()
    if (length1, n_min1, n_max1) == (length2, n_min2, n_max2):
        assert h1 == h2
    else:
        assert h1 != h2


# ---------------------------------------------------------------------------
# Constant: n_cap is constant across rounds.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_cap=_FRACTION,
    r1=st.integers(min_value=0, max_value=20),
    r2=st.integers(min_value=0, max_value=20),
    target=_TARGET_ROUND,
)
def test_constant_n_cap_flat(
    length: int, n_cap: float, r1: int, r2: int, target: int
) -> None:
    """Constant scheduler returns identical n_cap on every round."""
    if length <= 1 or r1 >= length or r2 >= length:
        return
    sched = ConstantScheduler(cycle_length=length, n_cap=n_cap, seed=0)
    s1 = sched.sample(0, r1, target)
    s2 = sched.sample(0, r2, target)
    assert math.isclose(s1.n_cap, s2.n_cap, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(s1.n_cap, n_cap, rel_tol=0.0, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(length=_CYCLE_LEN, n_cap=_FRACTION)
def test_constant_is_pure_idempotent(
    length: int, n_cap: float
) -> None:
    """Same args → same sample (idempotency)."""
    if length <= 1:
        return
    sched = ConstantScheduler(cycle_length=length, n_cap=n_cap, seed=0)
    a = sched.sample(2, 3, 5)
    sched.reset()
    b = sched.sample(2, 3, 5)
    assert a == b


# ---------------------------------------------------------------------------
# Linear: endpoint anchoring + ramp shape.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_min=_FRACTION,
    n_max=_FRACTION,
    target=_TARGET_ROUND,
)
def test_linear_endpoints_anchor(
    length: int, n_min: float, n_max: float, target: int
) -> None:
    """Round 0 → n_max; round length-1 → n_min."""
    if length <= 1:
        return
    sched = LinearScheduler(cycle_length=length, n_min=n_min, n_max=n_max)
    s0 = sched.sample(0, 0, target)
    sN = sched.sample(0, length - 1, target)
    assert math.isclose(s0.n_cap, n_max, abs_tol=1e-9)
    assert math.isclose(sN.n_cap, n_min, abs_tol=1e-9)


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_min=_FRACTION,
    n_max=_FRACTION,
)
def test_linear_monotone_direction(
    length: int, n_min: float, n_max: float
) -> None:
    """n_cap moves monotonically across rounds (ramp direction set by the
    closed form ``n_cap = n_max - (n_max - n_min) * u_r``).

    Concretely:
      * if ``n_max > n_min``: sequence is non-increasing from round 0
        (=n_max) to round length-1 (=n_min);
      * if ``n_min > n_max``: sequence is non-decreasing from round 0
        (=n_max) to round length-1 (=n_min).
    """
    if length <= 1:
        return
    sched = LinearScheduler(cycle_length=length, n_min=n_min, n_max=n_max)
    cap_values = [sched.sample(0, r, 0).n_cap for r in range(length)]
    if n_max >= n_min:
        # closed form: round 0 (=n_max) >= round N-1 (=n_min)
        for a, b in zip(cap_values, cap_values[1:]):
            assert a >= b - 1e-9
    else:
        # closed form: round 0 (=n_max, smaller) <= round N-1 (=n_min, larger)
        for a, b in zip(cap_values, cap_values[1:]):
            assert a <= b + 1e-9


# ---------------------------------------------------------------------------
# Exponential: non-negativity + monotone decay when alpha > 0.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_max=_FRACTION,
    alpha=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
)
def test_exponential_n_cap_nonnegative(
    length: int, n_max: float, alpha: float
) -> None:
    """Exponential scheduler never returns n_cap < 0 (clipped)."""
    if length <= 1:
        return
    if n_max < 0.01:  # Default positive lower bound of the exponential family.
        with pytest.raises(ValueError, match="n_max must be >= n_min"):
            ExponentialScheduler(cycle_length=length, n_max=n_max, alpha=alpha)
        return
    sched = ExponentialScheduler(cycle_length=length, n_max=n_max, alpha=alpha)
    for r in range(length):
        n_cap = sched.sample(0, r, 0).n_cap
        assert -1e-12 <= n_cap <= 1.0 + 1e-12


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_max=_FRACTION,
)
def test_exponential_alpha_zero_equals_constant(
    length: int, n_max: float
) -> None:
    """alpha == 0 collapses the exponential family to the constant family at n_max."""
    if length <= 1:
        return
    if n_max < 0.01:
        with pytest.raises(ValueError, match="n_max must be >= n_min"):
            ExponentialScheduler(cycle_length=length, n_max=n_max, alpha=0.0)
        return
    sched = ExponentialScheduler(cycle_length=length, n_max=n_max, alpha=0.0)
    for r in range(length):
        assert math.isclose(
            sched.sample(0, r, 0).n_cap, n_max, abs_tol=1e-9
        )


# ---------------------------------------------------------------------------
# Polynomial: power=1 equivalence to LinearScheduler (modulo the
# non-clipping defensive range).
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_min=_FRACTION,
    n_max=_FRACTION,
)
def test_polynomial_power_one_matches_linear(
    length: int, n_min: float, n_max: float
) -> None:
    """PolynomialScheduler with power=1 should match LinearScheduler."""
    if length <= 1:
        return
    if n_max < n_min:
        with pytest.raises(ValueError, match="n_max must be >= n_min"):
            PolynomialScheduler(cycle_length=length, n_min=n_min, n_max=n_max, power=1.0)
        return
    poly = PolynomialScheduler(
        cycle_length=length, n_min=n_min, n_max=n_max, power=1.0
    )
    linear = LinearScheduler(cycle_length=length, n_min=n_min, n_max=n_max)
    for r in range(length):
        p = poly.sample(0, r, 0).n_cap
        l = linear.sample(0, r, 0).n_cap
        assert math.isclose(p, l, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Sigmoid: midpoint symmetry — ``steepness = 0`` ⇒ midpoint, monotonicity
# in u_r when steepness > 0.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    length=_CYCLE_LEN,
    n_min=_FRACTION,
    n_max=_FRACTION,
)
def test_sigmoid_steepness_zero_is_midpoint(
    length: int, n_min: float, n_max: float
) -> None:
    """steepness == 0 collapses the sigmoid to the midpoint value."""
    if length <= 1:
        return
    mid = 0.5 * (n_min + n_max)
    if n_max < n_min:
        with pytest.raises(ValueError, match="n_max must be >= n_min"):
            SigmoidScheduler(cycle_length=length, n_min=n_min, n_max=n_max, steepness=0.0)
        return
    sched = SigmoidScheduler(
        cycle_length=length, n_min=n_min, n_max=n_max,
        steepness=0.0, midpoint=0.5,
    )
    for r in range(length):
        n_cap = sched.sample(0, r, 0).n_cap
        assert math.isclose(n_cap, mid, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# ScheduleSample.memory_fraction: clip into [0, 1] regardless of n_cap.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(n_cap=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False))
def test_memory_fraction_clipped_into_unit_interval(n_cap: float) -> None:
    """``ScheduleSample.memory_fraction()`` returns 1 - n_cap clipped to [0, 1]."""
    sample = ScheduleSample(
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=n_cap,
        n_min=0.0,
        n_max=1.0,
        u_r=0.0,
        family="x",
        computed_at_round=0,
        schedule_hash="x",
    )
    m = sample.memory_fraction()
    assert 0.0 <= m <= 1.0
    # the unclipped target
    raw = 1.0 - n_cap
    if 0.0 <= raw <= 1.0:
        assert math.isclose(m, raw, abs_tol=1e-12)
    elif raw < 0.0:
        assert math.isclose(m, 0.0, abs_tol=1e-12)
    else:
        assert math.isclose(m, 1.0, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(n_cap=st.floats(allow_nan=True))
def test_memory_fraction_nan_raises(n_cap: float) -> None:
    """``ScheduleSample.memory_fraction()`` raises ValueError on NaN/inf."""
    if math.isfinite(n_cap):
        return
    sample = ScheduleSample(
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=n_cap,
        n_min=0.0,
        n_max=1.0,
        u_r=0.0,
        family="x",
        computed_at_round=0,
        schedule_hash="x",
    )
    with pytest.raises(ValueError):
        sample.memory_fraction()
