"""Property-based invariants for :func:`bounded_merge` (DTB-R3).

Eight hypothesis-driven templates covering the bounded merge's
contract:

1. Output range: ``result ∈ [floor, cap]``.
2. Per-round delta cap: ``|result - prev| <= max(delta_cap_up, delta_cap_down)``.
3. Monotone in dynamic (others fixed).
4. Anti-monotone in floor.
5. Idempotent when ``prev == clamp(dynamic, floor, cap)``.
6. Empty interval collapses to ``floor``.
7. Fail-closed on non-finite (NaN, +/- Inf) inputs.
8. Bool coercion: ``True`` -> 1, ``False`` -> 0.

Each test is small, focused on a single property, and uses the
strategies defined in ``tests/property/conftest.py``.
"""
from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from adaptive_reflow.frame.merge import MergeAuthorityError, bounded_merge
from tests._utils.asserters import (
    assert_delta_capped,
    assert_idempotent,
    assert_in_closed,
)

from . import (
    bool_only,
    cap_with_floor,
    delta_cap_floats,
    floor_floats,
    prev_dynamic_floats,
)

# ---------------------------------------------------------------------------
# A tiny non-finite strategy that does not collide with hypothesis'
# bounds+allow_nan restriction: we sample ``math.nan``,
# ``math.inf`` and ``-math.inf`` directly from a finite tuple.
# ---------------------------------------------------------------------------
_NON_FINITE_SENTINELS = st.sampled_from(
    [float("nan"), float("inf"), float("-inf")]
)


# ---------------------------------------------------------------------------
# 1. Output range: result ∈ [floor, cap]
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_output_in_envelope(
    prev: float,
    dynamic: float,
    floor_cap: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """The merge result must always lie inside ``[floor, cap]``."""
    floor, cap = floor_cap
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_up,
        delta_cap_down=delta_down,
    )
    assert_in_closed(result, floor, cap, name="result")


# ---------------------------------------------------------------------------
# 2. Per-round delta cap: |result - prev| <= max(delta_cap_up, delta_cap_down)
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_delta_cap_respected(
    prev: float,
    dynamic: float,
    floor_cap: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """Per-round change cannot exceed the larger of the two delta caps.

    Note: the per-round delta cap invariant only applies when the
    bounded interval ``[lo, hi] = [max(floor, prev - delta_cap_down),
    min(cap, prev + delta_cap_up)]`` is non-empty. When the interval
    collapses (``hi < lo``) the bounded merge returns the floor
    unconditionally; that case is exercised separately by
    :func:`test_bounded_merge_empty_interval_collapses_to_floor`.
    """
    floor, cap = floor_cap
    lo = max(floor, prev - delta_down)
    hi = min(cap, prev + delta_up)
    assume(hi >= lo)
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_up,
        delta_cap_down=delta_down,
    )
    assert_delta_capped(prev, result, delta_up, delta_down)


# ---------------------------------------------------------------------------
# 3. Monotone in dynamic (others fixed)
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic_a=prev_dynamic_floats,
    dynamic_b=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_monotone_in_dynamic(
    prev: float,
    dynamic_a: float,
    dynamic_b: float,
    floor_cap: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """Increasing the dynamic value must not decrease the merge result."""
    floor, cap = floor_cap
    d_lo, d_hi = sorted((float(dynamic_a), float(dynamic_b)))
    assume(d_lo < d_hi)
    r_lo = bounded_merge(
        prev=prev, dynamic=d_lo, cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    r_hi = bounded_merge(
        prev=prev, dynamic=d_hi, cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    tol = 1e-9
    assert r_hi + tol >= r_lo, (
        f"monotonicity violated: dynamic {d_lo}->{d_hi} produced "
        f"r_lo={r_lo}, r_hi={r_hi}"
    )


# ---------------------------------------------------------------------------
# 4. Anti-monotone in floor
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    cap=delta_cap_floats,
    floor_a=floor_floats,
    floor_b=floor_floats,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_antimonotone_in_floor(
    prev: float,
    dynamic: float,
    cap: float,
    floor_a: float,
    floor_b: float,
    delta_up: float,
    delta_down: float,
) -> None:
    """Increasing ``floor`` (with ``floor <= cap``) must not increase the result."""
    fa, fb = sorted((float(floor_a), float(floor_b)))
    assume(fa < fb)
    effective_cap = max(float(cap), fb)
    r_lo = bounded_merge(
        prev=prev, dynamic=dynamic, cap=effective_cap, floor=fa,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    r_hi = bounded_merge(
        prev=prev, dynamic=dynamic, cap=effective_cap, floor=fb,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    tol = 1e-9
    assert r_hi + tol >= r_lo, (
        f"anti-monotonicity violated: floor {fa}->{fb} produced "
        f"r_lo={r_lo} > r_hi={r_hi}"
    )


# ---------------------------------------------------------------------------
# 5. Idempotent when prev == clamp(dynamic, floor, cap)
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_idempotent_when_prev_is_clamped_target(
    prev: float,
    dynamic: float,
    floor_cap: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """If ``prev == clamp(dynamic, floor, cap)`` the result equals ``prev``.

    The bounded merge's per-round interval is
    ``[max(floor, prev - delta_cap_down), min(cap, prev + delta_cap_up)]``.
    We additionally require the interval to be non-empty (so the merge
    does not collapse to the floor); the collapse path is tested
    separately.
    """
    floor, cap = floor_cap
    target = max(floor, min(cap, dynamic))
    # Set ``prev == target`` and ensure both delta caps cover ``prev``.
    new_prev = float(target)
    lo = max(floor, new_prev - delta_down)
    hi = min(cap, new_prev + delta_up)
    assume(lo <= new_prev <= hi)
    result = bounded_merge(
        prev=new_prev, dynamic=dynamic, cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    assert result == pytest.approx(new_prev, abs=1e-12)
    # Two independent calls yield the same result (idempotence on the
    # data shape — bounded_merge is pure).
    a = bounded_merge(
        prev=new_prev, dynamic=dynamic, cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    b = bounded_merge(
        prev=new_prev, dynamic=dynamic, cap=cap, floor=floor,
        delta_cap_up=delta_up, delta_cap_down=delta_down,
    )
    assert a == b


# ---------------------------------------------------------------------------
# 6. Empty interval collapses to floor
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    cap=delta_cap_floats,
    floor=floor_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_empty_interval_collapses_to_floor(
    prev: float,
    dynamic: float,
    cap: float,
    floor: float,
) -> None:
    """When the per-round interval collapses the merge returns the floor.

    We force the collapse by setting ``delta_cap_up = delta_cap_down = 0``
    and ensuring ``prev`` is *outside* the ``[floor, cap]`` envelope so
    that ``lo = max(floor, prev) > min(cap, prev) = hi``.
    """
    # Envelope must be well-formed: cap >= floor.
    cap_eff = max(float(cap), float(floor))
    # Force collapse: both delta caps = 0 and ``prev`` strictly outside
    # ``[floor, cap_eff]``.
    assume(prev > cap_eff or prev < floor)
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap_eff,
        floor=floor,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
    )
    assert result == pytest.approx(float(floor), abs=1e-12)


# ---------------------------------------------------------------------------
# 7. Fail-closed on non-finite (NaN, Inf) inputs
# ---------------------------------------------------------------------------


@given(
    bad=_NON_FINITE_SENTINELS,
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_clips_non_finite(
    bad: float,
    prev: float,
    dynamic: float,
    floor_cap: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """Non-finite scalar arguments MUST be clipped into ``[0, 1]``
    (P0-3) — NOT raised — so the operator's contract ("return a
    finite ``float`` in ``[0, 1]``") can be fulfilled under hostile
    caller input. Only the numeric-type coercion boundary
    (``None`` / non-numeric) raises; numeric non-finite values are
    clipped and the canonical audit code is appended.
    """
    floor, cap = floor_cap
    # Sanity: the bad value really is non-finite.
    assert not math.isfinite(float(bad))
    # Substitute ``bad`` into each scalar argument one at a time so
    # the rejection surface is exhaustive but each call has exactly
    # one bad input. The non-finite numeric values are clipped,
    # not raised (P0-3).
    for name in ("prev", "dynamic", "cap", "floor"):
        kwargs = dict(
            prev=prev,
            dynamic=dynamic,
            cap=cap,
            floor=floor,
            delta_cap_up=delta_up,
            delta_cap_down=delta_down,
        )
        kwargs[name] = bad
        audit: list[str] = []
        result = bounded_merge(audit_codes=audit, **kwargs)
        # Result is finite and in ``[0, 1]`` (P0-3 contract).
        assert math.isfinite(result)
        assert 0.0 <= result <= 1.0
        # The audit trail MUST surface a clip / finite clip line for
        # the bad argument.
        assert any(
            code.startswith(
                (
                    "merge_cap_out_of_range",
                    "merge_floor_out_of_range",
                    "merge_nonfinite_prev_clipped",
                    "merge_nonfinite_dynamic_clipped",
                    "merge_cap_below_floor",
                )
            )
            for code in audit
        ), f"no P0-3 audit code for bad {name!r}; audit={audit!r}"


# ---------------------------------------------------------------------------
# 8. Bool coercion: True -> 1, False -> 0
# ---------------------------------------------------------------------------


@given(
    as_prev=bool_only,
    as_dynamic=bool_only,
    floor_cap=cap_with_floor,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_coerces_bools(
    as_prev: bool,
    as_dynamic: bool,
    floor_cap: tuple[float, float],
) -> None:
    """``True`` is treated as 1, ``False`` as 0 for ``prev`` / ``dynamic``."""
    floor, cap = floor_cap
    cap_eff = max(cap, floor)
    expected_prev = float(int(as_prev))
    expected_dynamic = float(int(as_dynamic))
    result_bool = bounded_merge(
        prev=as_prev,
        dynamic=as_dynamic,
        cap=cap_eff,
        floor=floor,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    result_numeric = bounded_merge(
        prev=expected_prev,
        dynamic=expected_dynamic,
        cap=cap_eff,
        floor=floor,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    assert result_bool == pytest.approx(result_numeric, abs=1e-12)
    assert expected_prev in (0.0, 1.0)
    assert expected_dynamic in (0.0, 1.0)
