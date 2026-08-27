"""Property-based tests for the orchestrator-driven merge anchoring.

These tests cover two structural invariants of
:func:`adaptive_reflow.frame.merge.bounded_merge_with_schedule`:

1. **prev is required.** When the orchestrator-driven helper is
   called with ``prev=None`` the merge is fail-closed: the helper
   appends :data:`ERR_PREV_REQUIRED` to ``audit_codes`` and raises
   :class:`MergeAuthorityError`. The schedule's ``n_cap`` is the
   cap, never the prev.
2. **Result lies inside the envelope.** When ``prev`` is supplied
   the returned :class:`FactorValue` lies inside the
   ``[floor, cap]`` envelope chosen by the helper (the cap is the
   schedule's ``n_cap``; the floor is the per-channel fresh-noise
   floor mapping entry, or the schedule's ``n_cap``, or ``0.0`` in
   that priority order).

The tests use Hypothesis with the strategies declared in
``tests/property/conftest.py``. They are stdlib + hypothesis only.
"""
from __future__ import annotations

import sys
from contextlib import suppress
from pathlib import Path

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleSample,
    FactorValue,
)
from adaptive_reflow.frame.merge import (
    ERR_PREV_REQUIRED,
    MERGE_AUTHORITY_SCHEMA_VERSION,
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    MergeAuthorityError,
    bounded_merge_with_schedule,
)

from . import (
    cap_with_floor,
    delta_cap_floats,
    floor_floats,
    prev_dynamic_floats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schedule_sample(*, n_cap: float) -> CosineScheduleSample:
    """Build a deterministic :class:`CosineScheduleSample` for tests."""
    return CosineScheduleSample(
        schedule_hash=ArtifactHash("schedule-prop"),
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
# 1. prev=None is always rejected (fail-closed)
# ---------------------------------------------------------------------------


@given(
    n_cap=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor=floor_floats,
    delta_cap=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_with_schedule_always_rejects_none_prev(
    n_cap: float,
    dynamic: float,
    floor: float,
    delta_cap: float,
) -> None:
    """When ``prev=None`` the helper always refuses: it appends
    :data:`ERR_PREV_REQUIRED` to ``audit_codes`` and raises
    :class:`MergeAuthorityError`, regardless of the envelope / dynamic
    / delta-cap values.

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
            fresh_noise_floor=float(floor),
            delta_caps_by_channel={ChannelName("c0"): float(delta_cap)},
            fresh_noise_floor_by_channel={
                ChannelName("c0"): float(floor),
            },
            prev=None,
            audit_codes=audit_codes,
        )
    except MergeAuthorityError as exc:  # pragma: no cover - hypothesis
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


# ---------------------------------------------------------------------------
# 2. Result lies inside the envelope when prev is supplied
# ---------------------------------------------------------------------------


@given(
    n_cap=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    prev=prev_dynamic_floats,
    floor_cap=cap_with_floor,
    delta_cap=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_with_schedule_result_in_envelope(
    n_cap: float,
    dynamic: float,
    prev: float,
    floor_cap: tuple[float, float],
    delta_cap: float,
) -> None:
    """When ``prev`` is supplied, the returned :class:`FactorValue`
    lies inside the ``[floor, cap]`` envelope chosen by the helper.

    The cap is the schedule's ``n_cap``; the floor is the per-channel
    mapping entry. We build an envelope where ``floor <= cap <=
    n_cap`` and verify the merge result lies inside it.
    """
    floor, cap_from_pair = floor_cap
    # Clamp cap to ``n_cap`` so the envelope is well-formed and the
    # helper's chosen floor/cap are consistent.
    n_cap_clamped = max(float(n_cap), float(cap_from_pair))
    sample = _make_schedule_sample(n_cap=float(n_cap_clamped))
    effective_floor = min(float(floor), float(n_cap_clamped))
    audit_codes: list[str] = []
    result = bounded_merge_with_schedule(
        channel=ChannelName("c0"),
        dynamic=float(dynamic),
        schedule_sample=sample,
        fresh_noise_floor=None,
        delta_caps_by_channel={ChannelName("c0"): float(delta_cap)},
        fresh_noise_floor_by_channel={
            ChannelName("c0"): float(effective_floor),
        },
        prev=float(prev),
        audit_codes=audit_codes,
    )
    value = float(result)
    # The result must lie in ``[effective_floor, n_cap_clamped]``.
    assert effective_floor - 1e-9 <= value <= n_cap_clamped + 1e-9, (
        f"merge result {value} must lie inside envelope "
        f"[{effective_floor}, {n_cap_clamped}] "
        f"(dynamic={dynamic}, prev={prev}, audit_codes={audit_codes})"
    )
    # When ``prev`` is supplied the helper appends the anchor code.
    assert MERGE_PREV_ANCHORED_TO_LAST_EMITTED in audit_codes, (
        f"prev-anchored code must be appended when prev is supplied; "
        f"got audit_codes={audit_codes!r}"
    )
    # Schema version is the canonical 1.0.0 string (sanity check).
    assert MERGE_AUTHORITY_SCHEMA_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# 3. Schedule sample absence -> cap = 1.0, prev still required
# ---------------------------------------------------------------------------


@given(
    dynamic=prev_dynamic_floats,
    prev=prev_dynamic_floats,
    floor=floor_floats,
    delta_cap=delta_cap_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_with_schedule_no_sample_uses_unit_cap(
    dynamic: float,
    prev: float,
    floor: float,
    delta_cap: float,
) -> None:
    """When the schedule sample is ``None`` the helper falls back to
    ``cap=1.0`` (the canonical upper bound). The merge result must
    still lie inside ``[floor, 1.0]`` and the prev-anchored code must
    be appended.
    """
    effective_floor = min(float(floor), 1.0)
    audit_codes: list[str] = []
    result = bounded_merge_with_schedule(
        channel=ChannelName("c0"),
        dynamic=float(dynamic),
        schedule_sample=None,
        fresh_noise_floor=None,
        delta_caps_by_channel={ChannelName("c0"): float(delta_cap)},
        fresh_noise_floor_by_channel={
            ChannelName("c0"): float(effective_floor),
        },
        prev=float(prev),
        audit_codes=audit_codes,
    )
    value = float(result)
    assert effective_floor - 1e-9 <= value <= 1.0 + 1e-9, (
        f"merge result {value} must lie inside envelope "
        f"[{effective_floor}, 1.0]"
    )
    assert MERGE_PREV_ANCHORED_TO_LAST_EMITTED in audit_codes


# ---------------------------------------------------------------------------
# 4. Audit codes are never appended when prev=None (no MERGE_PREV_ANCHORED)
# ---------------------------------------------------------------------------


@given(
    n_cap=prev_dynamic_floats,
    dynamic=prev_dynamic_floats,
    floor=floor_floats,
    delta_cap=delta_cap_floats,
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
def test_bounded_merge_with_schedule_no_prev_anchor_when_prev_none(
    n_cap: float,
    dynamic: float,
    floor: float,
    delta_cap: float,
) -> None:
    """Sanity: when ``prev=None`` (fail-closed path) the
    prev-anchored audit code must NEVER be appended. Only the
    ``ERR_PREV_REQUIRED`` code is appended (before the raise).
    """
    sample = _make_schedule_sample(n_cap=float(n_cap))
    audit_codes: list[str] = []
    with suppress(MergeAuthorityError):
        bounded_merge_with_schedule(
            channel=ChannelName("c0"),
            dynamic=float(dynamic),
            schedule_sample=sample,
            fresh_noise_floor=None,
            delta_caps_by_channel={ChannelName("c0"): float(delta_cap)},
            fresh_noise_floor_by_channel={
                ChannelName("c0"): float(floor),
            },
            prev=None,
            audit_codes=audit_codes,
        )
    assert MERGE_PREV_ANCHORED_TO_LAST_EMITTED not in audit_codes, (
        f"prev-anchored code must not appear when prev is None; "
        f"got audit_codes={audit_codes!r}"
    )
    assert ERR_PREV_REQUIRED in audit_codes, (
        f"ERR_PREV_REQUIRED must appear when prev is None; "
        f"got audit_codes={audit_codes!r}"
    )


# Quietly silence the unused strategy import linter complaint.
_ = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)
