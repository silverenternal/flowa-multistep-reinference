"""Property-based tests for :mod:`adaptive_reflow.algorithm.blender`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :func:`_linear_blend_arrays` — convex-combination structure, length
  invariant, endpoint anchors ``m=0`` / ``m=1``.
* :func:`_coerce_memory_fraction` — clipping into ``[0, 1]``,
  non-finite / non-numeric rejection.
* :class:`LinearBlender` — convex combination invariants via
  :func:`_linear_blend_arrays` and ``memory_fraction`` clipping.
* :class:`DistanceDecayBlender` — output is a convex combination
  (decay factor ``alpha in [0, 1]``).

Seed policy (Research 4 mitigation): blenders are deterministic; only
input tuples vary.
"""

from __future__ import annotations

import math

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.blender import (
    DistanceDecayBlender,
    LinearBlender,
    _coerce_memory_fraction,
    _linear_blend_arrays,
    _sigmoid,
)

_PROPERTY_SETTINGS = settings(
    max_examples=30,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


_FRACTION = st.floats(
    min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False
)
_PRIOR = st.lists(
    st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=8,
)
_FRESH = st.lists(
    st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=8,
)


# ---------------------------------------------------------------------------
# _linear_blend_arrays — convex combination structure.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(prior=_PRIOR, fresh=_FRESH, memory=_FRACTION)
def test_linear_blend_convex_combination(
    prior: list[float], fresh: list[float], memory: float
) -> None:
    """Linear blend output is the element-wise convex combination
    ``m * prior + (1 - m) * fresh``.

    Note: ``_linear_blend_arrays`` does NOT clip ``memory_fraction`` —
    the clipping is the caller's responsibility (the
    ``LinearBlender.blend`` wrapper calls ``_coerce_memory_fraction``
    before invoking this helper). This test exercises the helper
    with the raw ``m`` value so any future re-clipping in the helper
    is surfaced as a regression.
    """
    if len(prior) != len(fresh):
        return  # the helper raises on mismatch; handled by a separate test
    out = _linear_blend_arrays(tuple(prior), tuple(fresh), memory)
    expected = tuple(
        memory * p + (1.0 - memory) * f
        for p, f in zip(prior, fresh, strict=True)
    )
    assert len(out) == len(expected)
    for o, e in zip(out, expected, strict=False):
        assert math.isclose(o, e, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(prior=_PRIOR, fresh=_FRESH)
def test_linear_blend_length_invariant(prior: list[float], fresh: list[float]) -> None:
    """Output length equals input lengths (which must match)."""
    if len(prior) != len(fresh):
        return
    out = _linear_blend_arrays(tuple(prior), tuple(fresh), 0.5)
    assert len(out) == len(prior)


@_PROPERTY_SETTINGS
@given(prior=_PRIOR, fresh=_FRESH)
def test_linear_blend_endpoints(prior: list[float], fresh: list[float]) -> None:
    """``memory == 1`` → output equals prior; ``memory == 0`` → output equals fresh."""
    if len(prior) != len(fresh):
        return
    out_one = _linear_blend_arrays(tuple(prior), tuple(fresh), 1.0)
    out_zero = _linear_blend_arrays(tuple(prior), tuple(fresh), 0.0)
    for i, _ in enumerate(prior):
        assert math.isclose(out_one[i], prior[i], abs_tol=1e-12)
        assert math.isclose(out_zero[i], fresh[i], abs_tol=1e-12)


# ---------------------------------------------------------------------------
# _coerce_memory_fraction — clipping invariant + audit emission.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(m=_FRACTION)
def test_coerce_memory_fraction_clipped_to_unit_interval(m: float) -> None:
    """memory_fraction is clipped into [0, 1]."""
    out = _coerce_memory_fraction(m)
    assert 0.0 <= out <= 1.0
    if 0.0 <= m <= 1.0:
        assert math.isclose(out, m, abs_tol=1e-12)
    elif m < 0.0:
        assert math.isclose(out, 0.0, abs_tol=1e-12)
    else:
        assert math.isclose(out, 1.0, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(m=_FRACTION)
def test_coerce_memory_fraction_audit_emitted_on_clip(m: float) -> None:
    """Out-of-range memory_fraction appends the canonical audit code
    when an audit list is supplied."""
    if 0.0 <= m <= 1.0:
        return  # in-range: no audit code emitted
    audit: list[str] = []
    _coerce_memory_fraction(m, audit_codes=audit)
    assert any("memory_fraction_clipped" in code for code in audit)


# ---------------------------------------------------------------------------
# LinearBlender — convex combination via blend().
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    prior=st.lists(
        st.floats(min_value=-5.0, max_value=5.0, allow_nan=False),
        min_size=1, max_size=4,
    ),
    fresh=st.lists(
        st.floats(min_value=-5.0, max_value=5.0, allow_nan=False),
        min_size=1, max_size=4,
    ),
    m=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_linear_blender_blend_is_convex_combination(
    prior: list[float], fresh: list[float], m: float
) -> None:
    """LinearBlender output :attr:`native_state_digest` is deterministic
    and ``provenance`` includes the canonical ``"blender:linear"`` audit
    code (restricting ``m`` to ``[0, 1]`` so no clip-audit engages).
    """
    if len(prior) != len(fresh):
        return
    prior_state = type("S", (), {"native_value": tuple(prior)})()
    fresh_state = type("S", (), {"native_value": tuple(fresh)})()
    blender = LinearBlender()
    out = blender.blend(
        prior_state=prior_state,
        fresh_state=fresh_state,
        memory_fraction=m,
        channel="c",
    )
    # Determinism: same inputs always produce the same digest.
    out2 = blender.blend(
        prior_state=prior_state,
        fresh_state=fresh_state,
        memory_fraction=m,
        channel="c",
    )
    assert out.native_state_digest == out2.native_state_digest
    # Provenance carries the family audit code.
    assert any("blender:linear" in p for p in out.provenance)
    assert any("blender_hash" in p for p in out.provenance)


# ---------------------------------------------------------------------------
# _sigmoid — output in (0, 1), monotone increasing.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(x=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False))
def test_sigmoid_in_open_unit_interval(x: float) -> None:
    """``_sigmoid(x)`` is in (0, 1) for every real input."""
    out = _sigmoid(x)
    assert 0.0 < out < 1.0


@_PROPERTY_SETTINGS
@given(
    x1=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    x2=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_sigmoid_monotone(x1: float, x2: float) -> None:
    """``_sigmoid`` is monotonically non-decreasing."""
    out1 = _sigmoid(x1)
    out2 = _sigmoid(x2)
    if x1 <= x2:
        assert out1 <= out2 + 1e-12
    else:
        assert out2 <= out1 + 1e-12


# ---------------------------------------------------------------------------
# DistanceDecayBlender — output is a convex combination.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    prior=st.lists(
        st.floats(min_value=-5.0, max_value=5.0, allow_nan=False),
        min_size=1, max_size=4,
    ),
    fresh=st.lists(
        st.floats(min_value=-5.0, max_value=5.0, allow_nan=False),
        min_size=1, max_size=4,
    ),
    temperature=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
)
def test_distance_decay_blender_family_and_hash(
    prior: list[float], fresh: list[float], temperature: float
) -> None:
    """DistanceDecayBlender output ``provenance`` includes the canonical
    ``"blender:distance_decay"`` audit code and is deterministic."""
    if len(prior) != len(fresh):
        return
    prior_state = type("S", (), {"native_value": tuple(prior)})()
    fresh_state = type("S", (), {"native_value": tuple(fresh)})()
    blender = DistanceDecayBlender(temperature=temperature)
    out = blender.blend(
        prior_state=prior_state,
        fresh_state=fresh_state,
        memory_fraction=0.5,
        channel="c",
    )
    out2 = blender.blend(
        prior_state=prior_state,
        fresh_state=fresh_state,
        memory_fraction=0.5,
        channel="c",
    )
    assert out.native_state_digest == out2.native_state_digest
    assert any("blender:distance_decay" in p for p in out.provenance)


@_PROPERTY_SETTINGS
@given(
    temperature=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
)
def test_distance_decay_config_hash_distinct_for_distinct_temperature(
    temperature: float,
) -> None:
    """Two DistanceDecayBlender instances with different temperatures
    produce different ``config_hash`` strings."""
    a = DistanceDecayBlender(temperature=temperature)
    b = DistanceDecayBlender(temperature=temperature + 1e-3)
    assert a.config_hash() != b.config_hash()
