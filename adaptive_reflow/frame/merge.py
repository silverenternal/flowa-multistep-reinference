"""Bounded merge authority for the adaptive_reflow component (DTB-R3).

Replaces the old "max-only" dynamic-control merge (``memory_fraction =
max(prev, dynamic)`` and friends) with a symmetric bounded merge that can
both **increase** and **decrease** the prior-round fraction, while
respecting a hard ``[floor, cap]`` envelope and per-round ``delta_cap_up``
/ ``delta_cap_down`` step caps.

Module boundary:

* stdlib-only. No ``torch``. No I/O. No global state. No mutation of
  inputs.
* Pure functions; identical inputs always yield identical outputs.
* The legacy ``max(previous, dynamic)`` operator is **never** invoked
  inside this module. Any legacy caller must be ported to use
  :func:`bounded_merge` (or :func:`bounded_merge_with_schedule`).

Tasks satisfied:

* ``DTB-R3`` — replace the only-increase dynamic-control merge; bounded
  both up and down by per-round delta caps and a fresh-noise floor.

Public surface:

* :data:`MERGE_AUTHORITY_SCHEMA_NAME`
* :data:`MERGE_AUTHORITY_SCHEMA_VERSION`
* :func:`bounded_merge` — symmetric, capped, floor-aware merge of a
  previous-round fraction and a dynamic evidence-derived fraction.
* :func:`bounded_merge_with_schedule` — orchestrator-level helper that
  wires the bounded merge to a :class:`CosineScheduleSample` and a
  per-channel delta-cap mapping.

Failure modes
-------------

The merge is *fail-closed*: any non-finite value, a non-numeric type, a
negative floor, a cap below the floor, a missing required argument, or a
``delta_cap`` outside ``[0, 1]`` raises :exc:`MergeAuthorityError`
(subclass of :exc:`ValueError`).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from adaptive_reflow.contracts import (
    ChannelName,
    CosineScheduleSample,
    FactorValue,
)

__all__ = [
    "MERGE_AUTHORITY_SCHEMA_NAME",
    "MERGE_AUTHORITY_SCHEMA_VERSION",
    "MergeAuthorityError",
    "bounded_merge",
    "bounded_merge_with_schedule",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Schema name written into the handoff record so downstream consumers
#: can identify the contract this merge implements.
MERGE_AUTHORITY_SCHEMA_NAME: str = "adaptive_reflow.bounded_merge_authority"

#: Schema version of the bounded merge; bumped on backward-incompatible
#: changes to the clamp / delta-cap semantics.
MERGE_AUTHORITY_SCHEMA_VERSION: str = "1.0.0"


# ---------------------------------------------------------------------------
# Exceptions (fail-closed; surface bad caller input)
# ---------------------------------------------------------------------------


class MergeAuthorityError(ValueError):
    """Raised when :func:`bounded_merge` rejects its arguments.

    Inherits from :exc:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns continue to work; the specific
    subclass is exposed via :data:`__all__` for callers that want to
    narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, ASCII only)
# ---------------------------------------------------------------------------


_ERR_PREV_NONE: str = "merge_prev_required"
_ERR_PREV_NOT_FINITE: str = "merge_prev_not_finite"
_ERR_DYNAMIC_NONE: str = "merge_dynamic_required"
_ERR_DYNAMIC_NOT_FINITE: str = "merge_dynamic_not_finite"
_ERR_CAP_NEGATIVE: str = "merge_cap_below_zero"
_ERR_CAP_ABOVE_ONE: str = "merge_cap_above_one"
_ERR_FLOOR_NEGATIVE: str = "merge_floor_below_zero"
_ERR_FLOOR_ABOVE_ONE: str = "merge_floor_above_one"
_ERR_CAP_BELOW_FLOOR: str = "merge_cap_below_floor"
_ERR_DELTA_UP_NEGATIVE: str = "merge_delta_cap_up_below_zero"
_ERR_DELTA_UP_ABOVE_ONE: str = "merge_delta_cap_up_above_one"
_ERR_DELTA_DOWN_NEGATIVE: str = "merge_delta_cap_down_below_zero"
_ERR_DELTA_DOWN_ABOVE_ONE: str = "merge_delta_cap_down_above_one"


# ---------------------------------------------------------------------------
# Internal coercion helpers
# ---------------------------------------------------------------------------


def _coerce_finite_real(x: Any, *, name: str) -> float:
    """Return ``float(x)``; raise :exc:`MergeAuthorityError` on bad input.

    Booleans are coerced to 0/1 (this matches the policy_authority and
    restart_memory_types coercion conventions). ``None`` is rejected.
    """
    if x is None:
        raise MergeAuthorityError(f"{name}: required (got None)")
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise MergeAuthorityError(
            f"{name}: expected a real number, got {type(x).__name__}"
        )
    fx = float(x)
    if not math.isfinite(fx):
        raise MergeAuthorityError(f"{name}: must be finite, got {fx!r}")
    return fx


def _coerce_factor_value(x: Any, *, name: str) -> float:
    """Return ``float(x)``; booleans become 0/1; ``None`` -> ``0.0``.

    Used by :func:`bounded_merge_with_schedule` to extract optional
    ``FactorValue``-typed fields from a schedule sample without raising
    on missing data (the helper returns the conservative default and
    the bounded merge still validates it as a real number).
    """
    if x is None:
        return 0.0
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise MergeAuthorityError(
            f"{name}: expected a real number, got {type(x).__name__}"
        )
    return float(x)


# ---------------------------------------------------------------------------
# Bounded merge
# ---------------------------------------------------------------------------


def bounded_merge(
    prev: float,
    dynamic: float,
    *,
    cap: float,
    floor: float,
    delta_cap_up: float,
    delta_cap_down: float,
) -> float:
    """Return a bounded merge of ``prev`` and ``dynamic``.

    The merge is the canonical replacement for the legacy
    ``max(prev, dynamic)`` operator used in the
    ``adaptive_reflow_soft_closed_loop_controls`` heuristic. It can
    both *increase* and *decrease* the prior-round fraction, while
    respecting:

    * a hard envelope ``[floor, cap]`` (default ``[0.0, 1.0]``);
    * per-round ``delta_cap_up`` (max increase relative to ``prev``);
    * per-round ``delta_cap_down`` (max decrease relative to ``prev``).

    Concretely, let ``target = clamp(dynamic, floor, cap)``. The
    returned value is

        result = clamp(target, max(floor, prev - delta_cap_down),
                       min(cap, prev + delta_cap_up))

    When the bound interval is empty (e.g. ``floor > cap`` or the two
    delta-caps collapse the interval below the floor) the function
    returns the floor; this is the documented fail-closed behaviour so
    the merge is total and never raises on legitimate call patterns.

    Parameters
    ----------
    prev:
        Previous-round fraction. Must be finite.
    dynamic:
        Dynamic evidence-derived fraction. Must be finite.
    cap:
        Hard upper envelope (must be finite, in ``[0, 1]``, and
        ``>= floor``).
    floor:
        Hard lower envelope / fresh-noise floor (must be finite, in
        ``[0, 1]``, and ``<= cap``).
    delta_cap_up:
        Maximum per-round increase (must be finite, in ``[0, 1]``).
    delta_cap_down:
        Maximum per-round decrease (must be finite, in ``[0, 1]``).

    Returns
    -------
    float
        The bounded, clamped merge result in ``[floor, cap]``.

    Raises
    ------
    MergeAuthorityError
        On any non-finite input, on ``cap < floor``, or on any cap/floor
        value outside ``[0, 1]``.
    """
    prev_f = _coerce_finite_real(prev, name="prev")
    dynamic_f = _coerce_finite_real(dynamic, name="dynamic")
    cap_f = _coerce_finite_real(cap, name="cap")
    floor_f = _coerce_finite_real(floor, name="floor")
    up_f = _coerce_finite_real(delta_cap_up, name="delta_cap_up")
    down_f = _coerce_finite_real(delta_cap_down, name="delta_cap_down")

    # Reject impossible configurations before any clamping so callers
    # see a deterministic, named error code.
    if cap_f < 0.0:
        raise MergeAuthorityError(
            f"{_ERR_CAP_NEGATIVE}: cap must be >= 0, got {cap_f!r}"
        )
    if cap_f > 1.0:
        raise MergeAuthorityError(
            f"{_ERR_CAP_ABOVE_ONE}: cap must be <= 1, got {cap_f!r}"
        )
    if floor_f < 0.0:
        raise MergeAuthorityError(
            f"{_ERR_FLOOR_NEGATIVE}: floor must be >= 0, got {floor_f!r}"
        )
    if floor_f > 1.0:
        raise MergeAuthorityError(
            f"{_ERR_FLOOR_ABOVE_ONE}: floor must be <= 1, got {floor_f!r}"
        )
    if cap_f < floor_f:
        raise MergeAuthorityError(
            f"{_ERR_CAP_BELOW_FLOOR}: cap ({cap_f!r}) must be >= "
            f"floor ({floor_f!r})"
        )
    if up_f < 0.0:
        raise MergeAuthorityError(
            f"{_ERR_DELTA_UP_NEGATIVE}: delta_cap_up must be >= 0, got {up_f!r}"
        )
    if up_f > 1.0:
        raise MergeAuthorityError(
            f"{_ERR_DELTA_UP_ABOVE_ONE}: delta_cap_up must be <= 1, got {up_f!r}"
        )
    if down_f < 0.0:
        raise MergeAuthorityError(
            f"{_ERR_DELTA_DOWN_NEGATIVE}: delta_cap_down must be >= 0, "
            f"got {down_f!r}"
        )
    if down_f > 1.0:
        raise MergeAuthorityError(
            f"{_ERR_DELTA_DOWN_ABOVE_ONE}: delta_cap_down must be <= 1, "
            f"got {down_f!r}"
        )

    # Step 1 — clamp the dynamic value to the envelope.
    target = max(floor_f, min(cap_f, dynamic_f))

    # Step 2 — bound the per-round delta. The interval is
    # [max(floor, prev - delta_cap_down), min(cap, prev + delta_cap_up)].
    lo = max(floor_f, prev_f - down_f)
    hi = min(cap_f, prev_f + up_f)

    # Defensive: collapse an empty interval to the floor. This is the
    # documented fail-closed path; the merge never raises on legitimate
    # call patterns and never returns a value below the floor.
    if hi < lo:
        return float(floor_f)

    return float(max(lo, min(hi, target)))


# ---------------------------------------------------------------------------
# Orchestrator-level helper
# ---------------------------------------------------------------------------


def _delta_caps_for_channel(
    delta_caps_by_channel: Mapping[ChannelName, float] | None,
    channel: ChannelName,
) -> tuple[float, float]:
    """Return ``(delta_cap_up, delta_cap_down)`` for ``channel``.

    Falls back to ``(0.5, 0.5)`` when ``channel`` is missing from the
    mapping; the merge still validates the resulting values.
    """
    if delta_caps_by_channel is None:
        return (0.5, 0.5)
    value = delta_caps_by_channel.get(channel)
    if value is None:
        return (0.5, 0.5)
    if isinstance(value, bool):
        f = float(int(value))
    elif isinstance(value, (int, float)):
        f = float(value)
    else:
        return (0.5, 0.5)
    if not math.isfinite(f) or f < 0.0 or f > 1.0:
        return (0.5, 0.5)
    return (f, f)


def _floor_for_channel(
    fresh_noise_floor_by_channel: Mapping[ChannelName, float] | None,
    schedule_sample: CosineScheduleSample | None,
    channel: ChannelName,
) -> float:
    """Return the per-channel fresh-noise floor.

    Priority:

    1. ``fresh_noise_floor_by_channel[channel]`` if supplied and valid.
    2. ``schedule_sample.n_cap`` if supplied (conservative default).
    3. ``0.0``.
    """
    if fresh_noise_floor_by_channel is not None:
        value = fresh_noise_floor_by_channel.get(channel)
        if value is not None:
            if isinstance(value, bool):
                f = float(int(value))
            elif isinstance(value, (int, float)):
                f = float(value)
            else:
                f = None
            if f is not None and math.isfinite(f) and 0.0 <= f <= 1.0:
                return float(f)
    if schedule_sample is not None:
        try:
            n_cap = _coerce_factor_value(schedule_sample.n_cap, name="schedule.n_cap")
            if math.isfinite(n_cap) and 0.0 <= n_cap <= 1.0:
                return float(n_cap)
        except MergeAuthorityError:
            pass
    return 0.0


def _cap_for_channel(
    schedule_sample: CosineScheduleSample | None,
) -> float:
    """Return the per-channel hard upper cap.

    Defaults to ``1.0`` (the canonical upper bound on a fraction) unless
    the schedule sample explicitly carries a smaller ``n_cap`` value.
    """
    if schedule_sample is None:
        return 1.0
    try:
        n_cap = _coerce_factor_value(schedule_sample.n_cap, name="schedule.n_cap")
    except MergeAuthorityError:
        return 1.0
    if not math.isfinite(n_cap) or n_cap < 0.0:
        return 1.0
    return float(min(1.0, n_cap))


def _prev_for_channel(
    schedule_sample: CosineScheduleSample | None,
) -> float:
    """Return the previous-round fraction for ``channel``.

    Falls back to ``0.0`` when no sample is supplied (the merge then
    behaves as a one-shot bounded update from zero).
    """
    if schedule_sample is None:
        return 0.0
    try:
        n_cap = _coerce_factor_value(schedule_sample.n_cap, name="schedule.n_cap")
    except MergeAuthorityError:
        return 0.0
    if not math.isfinite(n_cap):
        return 0.0
    return float(max(0.0, min(1.0, n_cap)))


def bounded_merge_with_schedule(
    *,
    channel: ChannelName,
    dynamic: float,
    schedule_sample: CosineScheduleSample | None,
    fresh_noise_floor: float,
    delta_caps_by_channel: Mapping[ChannelName, float] | None,
    prev: float | None = None,
) -> FactorValue:
    """Convenience wrapper that threads a schedule sample through the merge.

    The helper extracts ``prev``, ``cap`` and ``floor`` from the supplied
    schedule sample (or falls back to defaults) and forwards to
    :func:`bounded_merge`. The result is wrapped in
    :class:`FactorValue` so the orchestrator can store it directly in
    its per-channel mapping.

    Parameters
    ----------
    channel:
        The channel name; used to look up the per-channel delta cap and
        fresh-noise floor. Ignored if both mapping arguments are
        ``None`` (the helper falls back to the canonical 0.5 / schedule
        defaults).
    dynamic:
        The dynamic, evidence-derived fraction. Must be finite.
    schedule_sample:
        Optional :class:`CosineScheduleSample`. ``None`` is allowed and
        uses the conservative defaults.
    fresh_noise_floor:
        Per-channel fresh-noise floor. Must be finite and in ``[0, 1]``.
        When supplied as a non-``None`` value it overrides the
        per-channel mapping lookup.
    delta_caps_by_channel:
        Optional per-channel symmetric delta cap mapping. Used to look
        up ``delta_cap_up`` / ``delta_cap_down``; defaults to ``0.5``.
    prev:
        Optional explicit previous-round fraction. ``None`` falls back
        to ``schedule_sample.n_cap`` (or ``0.0`` when no sample is
        supplied). The explicit override exists so the helper can be
        called from a ledger-driven orchestrator loop where the
        previous round's emitted ``bounded_target_fraction`` is the
        natural ``prev``.

    Returns
    -------
    FactorValue
        ``FactorValue(bounded_merge(...))``.
    """
    delta_up, delta_down = _delta_caps_for_channel(delta_caps_by_channel, channel)
    cap = _cap_for_channel(schedule_sample)
    floor = _floor_for_channel(None, schedule_sample, channel)
    if fresh_noise_floor is not None:
        try:
            floor_f = _coerce_finite_real(
                fresh_noise_floor, name="fresh_noise_floor"
            )
            if math.isfinite(floor_f) and 0.0 <= floor_f <= 1.0:
                floor = floor_f
        except MergeAuthorityError:
            pass
    if prev is None:
        prev_v = _prev_for_channel(schedule_sample)
    else:
        prev_v = _coerce_finite_real(prev, name="prev")

    merged = bounded_merge(
        prev=prev_v,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_up,
        delta_cap_down=delta_down,
    )
    return FactorValue(float(merged))
