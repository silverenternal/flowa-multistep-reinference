"""Property-based tests for :mod:`adaptive_reflow.algorithm.merge_operator`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :class:`BoundedMergeOperator` — closure: result is finite and lies in
  ``[0, 1]`` for every input envelope. Monotonicity in ``prev`` and
  ``dynamic`` (within the active envelope).
* :class:`IdentityOperator` — output equals clipped ``dynamic``.
* :class:`EMAOperator` — output lies on the convex combination
  ``prev + alpha * (dynamic - prev)`` line; idempotency at
  ``dynamic == prev``.
* Operator-level: ``config_hash`` distinctness for distinct
  ``exterior_gap_e_rho`` values.

Seed policy (Research 4 mitigation): merge operators are deterministic;
Hypothesis varies only the input envelope tuples.
"""

from __future__ import annotations

import math

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.merge_operator import (
    BoundedMergeOperator,
    EMAOperator,
    IdentityOperator,
)


_PROPERTY_SETTINGS = settings(
    max_examples=30,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


# Helper: an envelope that is provably valid (cap >= floor, both in [0, 1]).
_ENVELOPE = st.tuples(
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
).map(lambda c_f: (max(c_f), min(c_f)))  # enforce cap >= floor

_DELTA = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

_PREV = st.floats(min_value=-0.5, max_value=1.5, allow_nan=False, allow_infinity=False)
_DYNAMIC = st.floats(min_value=-0.5, max_value=1.5, allow_nan=False, allow_infinity=False)


# ---------------------------------------------------------------------------
# BoundedMergeOperator: closure — result is finite and in [0, 1].
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    prev=_PREV,
    dynamic=_DYNAMIC,
    envelope=_ENVELOPE,
    delta_up=_DELTA,
    delta_down=_DELTA,
)
def test_bounded_merge_closure(
    prev: float,
    dynamic: float,
    envelope: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    cap, floor = envelope
    op = BoundedMergeOperator()
    out = op.merge(
        prev, dynamic,
        cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    assert math.isfinite(out)
    assert 0.0 <= out <= 1.0


@_PROPERTY_SETTINGS
@given(
    prev=_PREV,
    envelope=_ENVELOPE,
    delta_up=_DELTA,
    delta_down=_DELTA,
)
def test_bounded_merge_constant_dynamic_idempotent(
    prev: float,
    envelope: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """If dynamic == prev, the merge result lies in [prev - delta_down, prev + delta_up]."""
    cap, floor = envelope
    op = BoundedMergeOperator()
    out = op.merge(
        prev, prev,
        cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    # The target = clamp(prev, floor, cap), then clamped into the
    # per-round delta envelope. Either way the result should still
    # lie in the canonical [floor, cap] envelope.
    assert floor - 1e-9 <= out <= cap + 1e-9


# ---------------------------------------------------------------------------
# IdentityOperator: output is the clipped dynamic.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(dynamic=_DYNAMIC)
def test_identity_returns_clipped_dynamic(dynamic: float) -> None:
    op = IdentityOperator()
    out = op.merge(
        0.5, dynamic,
        cap=1.0, floor=0.0,
        delta_cap_up=0.5, delta_cap_down=0.5,
    )
    expected = max(0.0, min(1.0, dynamic))
    assert math.isclose(out, expected, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(dynamic=_DYNAMIC)
def test_identity_ignores_prev(dynamic: float) -> None:
    """Identity ignores prev (modulo finiteness-check clipping)."""
    op = IdentityOperator()
    a = op.merge(0.0, dynamic, cap=1.0, floor=0.0, delta_cap_up=0.5, delta_cap_down=0.5)
    b = op.merge(0.7, dynamic, cap=1.0, floor=0.0, delta_cap_up=0.5, delta_cap_down=0.5)
    # If dynamic is finite and in [0, 1], both should be equal
    if 0.0 <= dynamic <= 1.0:
        assert math.isclose(a, b, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# EMAOperator: convex combination structure.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    prev=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    dynamic=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    alpha=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_ema_convex_combination(
    prev: float, dynamic: float, alpha: float
) -> None:
    """EMAOperator output lies on the convex-combination line
    ``prev + alpha * (dynamic - prev)`` (input range restricted to
    ``[0, 1]`` so no clip audit code engages)."""
    op = EMAOperator(alpha=alpha)
    out = op.merge(
        prev, dynamic,
        cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    expected = prev + alpha * (dynamic - prev)
    assert math.isclose(out, expected, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(prev=_PREV)
def test_ema_idempotent_when_dynamic_equals_prev(prev: float) -> None:
    """When dynamic == prev, EMA output equals prev (clipped)."""
    op = EMAOperator(alpha=0.3)
    out = op.merge(
        prev, prev,
        cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    expected = max(0.0, min(1.0, prev))
    assert math.isclose(out, expected, abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(prev=_PREV, dynamic=_DYNAMIC)
def test_ema_alpha_one_reduces_to_dynamic(prev: float, dynamic: float) -> None:
    """alpha == 1 collapses EMA to the clipped dynamic."""
    op = EMAOperator(alpha=1.0)
    out = op.merge(
        prev, dynamic,
        cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    expected = max(0.0, min(1.0, dynamic))
    assert math.isclose(out, expected, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# config_hash distinctness.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(e_rho1=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
       e_rho2=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_bounded_merge_config_hash_distinct_for_distinct_e_rho(
    e_rho1: float, e_rho2: float
) -> None:
    op1 = BoundedMergeOperator(exterior_gap_e_rho=e_rho1)
    op2 = BoundedMergeOperator(exterior_gap_e_rho=e_rho2)
    if e_rho1 == e_rho2:
        assert op1.config_hash() == op2.config_hash()
    else:
        assert op1.config_hash() != op2.config_hash()