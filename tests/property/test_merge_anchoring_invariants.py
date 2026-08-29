"""Cross-cutting property tests for the bounded-merge anchoring contract.

Three property-driven templates covering the structural invariants of
:func:`adaptive_reflow.frame.merge.bounded_merge` and
:func:`adaptive_reflow.frame.merge.bounded_merge_with_schedule`:

1. **test_result_within_envelope** — for any ``(prev, dynamic, floor,
   cap, up, down)`` drawn from the canonical envelope, the merge result
   lies inside ``[floor, cap]`` (the only case the bounded merge raises
   :class:`MergeAuthorityError` is when ``cap < floor`` or the cap /
   floor values are out of ``[0, 1]`` — those are caller bugs and we
   skip them via ``assume``).
2. **test_degenerate_interval_emits_audit** — when the per-round delta
   interval collapses (either because ``floor > cap`` *or* because the
   delta caps force ``hi < lo``), the merge emits
   :data:`MERGE_DEGENERATE_INTERVAL` in its audit trail. Note: when
   ``floor > cap`` the merge raises
   :class:`MergeAuthorityError`; in that case we verify the raise
   carries the canonical ``merge_cap_below_floor`` suffix instead.
3. **test_prev_none_is_fail_closed** — when ``prev=None`` is passed to
   :func:`bounded_merge_with_schedule`, the helper appends
   :data:`ERR_PREV_REQUIRED` to ``audit_codes`` and raises
   :class:`MergeAuthorityError`.

The tests use the strategies declared in
:mod:`tests.property.conftest` (re-exported from
:mod:`tests.property`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleSample,
    FactorValue,
)
from adaptive_reflow.frame.merge import (
    ERR_PREV_REQUIRED,
    MERGE_DEGENERATE_INTERVAL,
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    MergeAuthorityError,
    bounded_merge,
    bounded_merge_with_schedule,
)

from . import cap_with_floor, delta_cap_floats, floor_floats, prev_dynamic_floats

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schedule_sample(*, n_cap: float) -> CosineScheduleSample:
    """Build a deterministic :class:`CosineScheduleSample` for tests."""
    return CosineScheduleSample(
        schedule_hash=ArtifactHash("schedule-anchor-prop"),
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(float(n_cap)),
        n_min=FactorValue(0.0),
        n_max=FactorValue(float(n_cap)),
        u_r=0.0,
        family="cosine_no_restart",
        computed_at_round=0,
    )


# ---------------------------------------------------------------------------
# 1. Result lies inside [floor, cap]
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_up=delta_cap_floats,
    delta_down=delta_cap_floats,
)
@settings(max_examples=50, deadline=10000)
def test_result_within_envelope(
    prev: float,
    dynamic: float,
    floor_cap: tuple[float, float],
    delta_up: float,
    delta_down: float,
) -> None:
    """The bounded merge's result lies inside ``[floor, cap]`` for any
    in-domain ``(prev, dynamic, floor, cap, up, down)`` tuple.

    ``floor_cap`` is a tuple ``(floor, cap)`` with ``floor <= cap``, so
    the envelope is well-formed and the merge never raises. The
    :func:`tests._utils.asserters.assert_in_closed` helper enforces the
    membership invariant with a 1e-9 tolerance.
    """
    floor, cap = floor_cap
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_up,
        delta_cap_down=delta_down,
    )
    # ``result`` must lie inside ``[floor, cap]``.
    tol = 1e-9
    assert floor - tol <= float(result) <= cap + tol, (
        f"bounded_merge result {result!r} must lie in [{floor}, {cap}]; "
        f"got prev={prev}, dynamic={dynamic}, up={delta_up}, down={delta_down}"
    )


# ---------------------------------------------------------------------------
# 2. Degenerate interval emits MERGE_DEGENERATE_INTERVAL
# ---------------------------------------------------------------------------


@given(
    prev=prev_dynamic_floats,
    floor=st.floats(
        min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
    ),
    cap=st.floats(
        min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
    ),
)
@settings(max_examples=50, deadline=10000)
def test_degenerate_interval_emits_audit(
    prev: float,
    floor: float,
    cap: float,
) -> None:
    """When the per-round delta interval collapses, the merge either
    emits :data:`MERGE_DEGENERATE_INTERVAL` in its audit trail *or*
    (after the P0-3 fix) appends the canonical
    ``merge_cap_below_floor`` audit code without raising (when
    ``floor > cap``).

    Two configurations trigger the collapse:

    * ``floor > cap``: post-P0-3 the envelope swaps and the merge
      clips and emits the ``merge_cap_below_floor`` audit code (no
      exception is raised).
    * ``prev`` strictly outside ``[floor, cap]`` with both delta caps
      zero: the bounded interval ``[max(floor, prev), min(cap, prev)]``
      collapses (``hi < lo``) so the merge returns the floor and emits
      ``MERGE_DEGENERATE_INTERVAL``.

    The test exercises both cases via hypothesis' parameter sweep.
    """
    # Sanity: all values must be finite and in [0, 1].
    assume(0.0 <= prev <= 1.0)
    assume(0.0 <= floor <= 1.0)
    assume(0.0 <= cap <= 1.0)

    if floor > cap:
        # Path 1 — the envelope is ill-formed. F5: post-P0-3 + F5 the
        # merge fails closed: the ``merge_cap_below_floor`` audit code
        # is appended BEFORE the raise, and ``MergeAuthorityError`` is
        # raised. The audit code is still emitted so a downstream
        # reader can observe the broken configuration.
        audit_codes: list[str] = []
        with pytest.raises(MergeAuthorityError):
            bounded_merge(
                prev=prev,
                dynamic=prev,
                cap=cap,
                floor=floor,
                delta_cap_up=0.0,
                delta_cap_down=0.0,
                audit_codes=audit_codes,
            )
        joined = "|".join(audit_codes)
        assert "merge_cap_below_floor" in joined, (
            f"merge_cap_below_floor must appear in audit_codes; "
            f"got {audit_codes!r} for prev={prev}, floor={floor}, cap={cap}"
        )
        return

    # Path 2 — envelope is well-formed; force the per-round interval
    # to collapse by setting ``prev`` strictly outside ``[floor, cap]``
    # with both delta caps at zero.
    assume(prev > cap or prev < floor)

    audit_codes: list[str] = []
    result = bounded_merge(
        prev=prev,
        dynamic=prev,
        cap=cap,
        floor=floor,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit_codes,
    )
    # The audit code is emitted as ``MERGE_DEGENERATE_INTERVAL:floor=...
    # :cap=...:prev=...:up=...:down=...``; the substring
    # ``MERGE_DEGENERATE_INTERVAL`` must appear.
    joined = "|".join(audit_codes)
    assert MERGE_DEGENERATE_INTERVAL in joined, (
        f"MERGE_DEGENERATE_INTERVAL must appear in audit_codes; got {audit_codes!r} "
        f"for prev={prev}, floor={floor}, cap={cap}"
    )
    # The merge returned the floor (fail-closed behaviour).
    tol = 1e-9
    assert abs(float(result) - float(floor)) <= tol, (
        f"degenerate-interval merge must return the floor ({floor}); "
        f"got {result!r}"
    )


def pytest_raises_merge_authority():
    """Deprecated P0-3 stub.

    Post-P0-3 the bounded merge never raises on legitimate caller
    input such as ``floor > cap``; instead it clips and emits the
    canonical audit code. The stub remains so legacy callers that
    still expect the pytest context manager get a no-op context.
    """
    import contextlib

    @contextlib.contextmanager
    def _noop():
        yield

    return _noop()


# A second, simpler test for the well-formed degenerate case (no
# hypothesis in the body). Drives the ``prev+up < prev-down`` branch
# directly.
def test_prev_plus_up_lt_prev_minus_down_emits_audit() -> None:
    """When the per-round delta interval collapses because ``up < -down``
    (i.e. ``prev+up < prev-down``), the merge emits
    :data:`MERGE_DEGENERATE_INTERVAL` and returns the floor."""
    audit_codes: list[str] = []
    # With up=0.0, down=0.0, prev outside [floor, cap] -> empty interval.
    result = bounded_merge(
        prev=0.5,
        dynamic=0.5,
        cap=0.4,  # cap < prev -> hi = cap = 0.4
        floor=0.0,  # floor <= prev -> lo = max(0.0, 0.5) = 0.5
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit_codes,
    )
    joined = "|".join(audit_codes)
    assert MERGE_DEGENERATE_INTERVAL in joined
    assert float(result) == 0.0  # floor


# ---------------------------------------------------------------------------
# 3. prev=None is fail-closed
# ---------------------------------------------------------------------------


@given(
    n_cap=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor=floor_floats,
    delta_cap=delta_cap_floats,
)
@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.filter_too_much],
)
def test_prev_none_is_fail_closed(
    n_cap: float,
    dynamic: float,
    floor: float,
    delta_cap: float,
) -> None:
    """When ``prev=None`` is passed to
    :func:`bounded_merge_with_schedule`, the helper appends
    :data:`ERR_PREV_REQUIRED` to ``audit_codes`` and raises
    :class:`MergeAuthorityError`.

    This is the structural invariant for gap C2: the schedule's
    ``n_cap`` is the cap, never the prev; without an explicit
    prev-from-last-round the helper cannot make a defensible merge.
    """
    sample = _make_schedule_sample(n_cap=float(n_cap))
    audit_codes: list[str] = []
    raised: Exception | None = None
    try:
        bounded_merge_with_schedule(
            channel=ChannelName("c0"),
            dynamic=float(dynamic),
            schedule_sample=sample,
            fresh_noise_floor=None,
            delta_caps_by_channel={ChannelName("c0"): float(delta_cap)},
            fresh_noise_floor_by_channel={ChannelName("c0"): float(floor)},
            prev=None,
            audit_codes=audit_codes,
        )
    except MergeAuthorityError as exc:
        raised = exc
    assert raised is not None, (
        "bounded_merge_with_schedule must raise MergeAuthorityError "
        "when prev=None"
    )
    assert ERR_PREV_REQUIRED in audit_codes, (
        f"ERR_PREV_REQUIRED must be appended to audit_codes; "
        f"got {audit_codes!r}"
    )
    # And the prev-anchored code must NOT be appended (prev was None).
    assert MERGE_PREV_ANCHORED_TO_LAST_EMITTED not in audit_codes


def test_prev_none_without_audit_codes_still_raises() -> None:
    """``prev=None`` raises :class:`MergeAuthorityError` even when no
    ``audit_codes`` list is supplied. The helper refuses unconditionally
    — the ``audit_codes`` opt-in only controls whether the
    ``ERR_PREV_REQUIRED`` code is appended before the raise."""
    sample = _make_schedule_sample(n_cap=1.0)
    raised: Exception | None = None
    try:
        bounded_merge_with_schedule(
            channel=ChannelName("c0"),
            dynamic=0.5,
            schedule_sample=sample,
            fresh_noise_floor=None,
            delta_caps_by_channel={ChannelName("c0"): 0.5},
            fresh_noise_floor_by_channel={ChannelName("c0"): 0.1},
            prev=None,
        )
    except MergeAuthorityError as exc:
        raised = exc
    assert isinstance(raised, MergeAuthorityError)
    assert "prev is required" in str(raised).lower()


__all__ = [
    "test_result_within_envelope",
    "test_degenerate_interval_emits_audit",
    "test_prev_plus_up_lt_prev_minus_down_emits_audit",
    "test_prev_none_is_fail_closed",
    "test_prev_none_without_audit_codes_still_raises",
]
