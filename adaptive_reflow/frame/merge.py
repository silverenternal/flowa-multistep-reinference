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
    "ERR_PREV_REQUIRED",
    "MERGE_AUTHORITY_SCHEMA_NAME",
    "MERGE_AUTHORITY_SCHEMA_VERSION",
    "MERGE_DEGENERATE_INTERVAL",
    "MERGE_FLOOR_FALLBACK",
    "MERGE_PREV_ANCHORED_TO_LAST_EMITTED",
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


#: Audit code emitted when the per-round delta interval collapses to
#: an empty range (``hi < lo``) so the merge returns the floor. The
#: code carries the envelope values so a downstream audit reader can
#: reproduce the degenerate configuration.
MERGE_DEGENERATE_INTERVAL: str = "merge_degenerate_interval"

#: Audit code emitted when the per-channel fresh-noise floor has to
#: fall back to the schedule's ``n_cap`` (or ``0.0`` when no sample
#: was supplied). This signals that the config-level per-channel
#: floor mapping was missing for the requested channel.
MERGE_FLOOR_FALLBACK: str = "merge_floor_fallback_to_schedule_default"

#: Audit code emitted whenever the orchestrator-driven merge is
#: anchored on a ``prev`` value that came from the previous round's
#: emitted ``bounded_target_fraction`` (i.e. not from the schedule's
#: ``n_cap``). The schedule value is the cap, never the prev.
MERGE_PREV_ANCHORED_TO_LAST_EMITTED: str = "merge_prev_anchored_to_last_emitted"

#: Error code raised when the orchestrator-driven merge path is
#: asked to merge without supplying ``prev``. The schedule's
#: ``n_cap`` is the cap; the prev must come from the previous
#: round's emitted ``bounded_target_fraction``. See
#: :class:`MergeAuthorityError`.
ERR_PREV_REQUIRED: str = "merge_prev_required"

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
    audit_codes: list[str] | None = None,
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
    When ``audit_codes`` is supplied, the merge appends
    :data:`MERGE_DEGENERATE_INTERVAL` (with the envelope values
    embedded for forensic reconstruction) before returning the floor;
    when ``audit_codes`` is ``None`` the collapse is silent for
    back-compat with callers that do not opt into audit emission.

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
    audit_codes:
        Optional mutable list that the merge appends diagnostic codes
        to. When the per-round delta interval is empty (i.e. the
        bounded merge collapses to the floor) the merge appends
        :data:`MERGE_DEGENERATE_INTERVAL` with the envelope values
        embedded. When ``None``, no codes are emitted (the collapse
        is silent for back-compat).

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
    # call patterns and never returns a value below the floor. When
    # the caller opted into audit emission, we surface the collapse so
    # downstream consumers can audit-replay it.
    if hi < lo:
        if audit_codes is not None:
            audit_codes.append(
                f"{MERGE_DEGENERATE_INTERVAL}:floor={floor_f:.6f}"
                f":cap={cap_f:.6f}:prev={prev_f:.6f}"
                f":up={up_f:.6f}:down={down_f:.6f}"
            )
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
    fresh_noise_floor: float | None,
    fresh_noise_floor_by_channel: Mapping[ChannelName, float] | None,
    schedule_sample: CosineScheduleSample | None,
    channel: ChannelName,
    audit_codes: list[str] | None = None,
) -> float:
    """Return the per-channel fresh-noise floor with explicit precedence.

    Priority (highest first):

    1. ``fresh_noise_floor`` arg, when supplied as a non-``None`` value
       that is finite and in ``[0, 1]``. The caller-supplied argument
       is the authoritative override (e.g. an explicit
       ``floor_for_channel(channel)`` value forwarded by the
       orchestrator's decision).
    2. ``fresh_noise_floor_by_channel[channel]``, when the mapping
       supplies a finite value in ``[0, 1]``. The config-level
       per-channel floor is the canonical "no override" default.
    3. ``schedule_sample.n_cap``, when a schedule sample is supplied
       and its ``n_cap`` is finite and in ``[0, 1]``. This is the
       conservative "no override, no config" default; the audit code
       :data:`MERGE_FLOOR_FALLBACK` is appended so the fallback is
       observable.
    4. ``0.0`` as the last-resort default. The audit code
       :data:`MERGE_FLOOR_FALLBACK` is appended.
    """
    # Step 1 — explicit ``fresh_noise_floor`` argument.
    if fresh_noise_floor is not None:
        try:
            f_floor = _coerce_factor_value(
                fresh_noise_floor, name="fresh_noise_floor"
            )
        except MergeAuthorityError:
            f_floor = None
        if f_floor is not None and math.isfinite(f_floor) and 0.0 <= f_floor <= 1.0:
            return float(f_floor)
    # Step 2 — config-level per-channel mapping.
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
    # Step 3 — schedule_sample.n_cap as the conservative default.
    if schedule_sample is not None:
        try:
            n_cap = _coerce_factor_value(schedule_sample.n_cap, name="schedule.n_cap")
            if math.isfinite(n_cap) and 0.0 <= n_cap <= 1.0:
                if audit_codes is not None:
                    audit_codes.append(MERGE_FLOOR_FALLBACK)
                return float(n_cap)
        except MergeAuthorityError:
            pass
    # Step 4 — last-resort default; still surface the fallback.
    if audit_codes is not None:
        audit_codes.append(MERGE_FLOOR_FALLBACK)
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


def bounded_merge_with_schedule(
    *,
    channel: ChannelName,
    dynamic: float,
    schedule_sample: CosineScheduleSample | None,
    fresh_noise_floor: float | None,
    delta_caps_by_channel: Mapping[ChannelName, float] | None,
    fresh_noise_floor_by_channel: Mapping[ChannelName, float] | None = None,
    prev: float | None = None,
    audit_codes: list[str] | None = None,
) -> FactorValue:
    """Convenience wrapper that threads a schedule sample through the merge.

    The helper extracts ``cap`` from the supplied schedule sample and
    the floor from the per-channel fresh-noise floor mapping (or the
    ``fresh_noise_floor`` override), then forwards to
    :func:`bounded_merge`. The result is wrapped in
    :class:`FactorValue` so the orchestrator can store it directly in
    its per-channel mapping.

    The helper enforces two structural invariants on the orchestrator
    path:

    * The **cap** always comes from ``schedule_sample.n_cap`` (or
      ``1.0`` when no sample is supplied); the schedule value is the
      cap, never the prev.
    * The **prev** must come from the previous round's emitted
      ``bounded_target_fraction``. ``prev=None`` is rejected with
      :class:`MergeAuthorityError` (``ERR_PREV_REQUIRED``); the helper
      does NOT silently fall back to the schedule's ``n_cap`` because
      doing so would double-count the schedule value (as both the cap
      and the prev) and erase any ledger-driven information.

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
        Optional explicit fresh-noise floor override. When non-``None``
        it overrides the per-channel mapping lookup. ``None`` lets the
        helper consult ``fresh_noise_floor_by_channel`` instead.
    delta_caps_by_channel:
        Optional per-channel symmetric delta cap mapping. Used to look
        up ``delta_cap_up`` / ``delta_cap_down``; defaults to ``0.5``.
    fresh_noise_floor_by_channel:
        Optional config-level per-channel fresh-noise floor mapping.
        Used when ``fresh_noise_floor`` is ``None`` to honour the
        configured floor rather than silently ignoring it.
    prev:
        The previous round's emitted ``bounded_target_fraction`` for
        ``channel``. ``None`` is rejected with
        :class:`MergeAuthorityError` (``ERR_PREV_REQUIRED``) when the
        caller has opted into ``audit_codes``; otherwise the helper
        refuses by raising unconditionally. The caller (engine /
        orchestrator) is responsible for surfacing the error in its
        :class:`EngineRoundResult` audit trail.
    audit_codes:
        Optional mutable list that the merge appends diagnostic codes
        to. ``MERGE_PREV_ANCHORED_TO_LAST_EMITTED`` is appended when
        ``prev`` is supplied (so a downstream audit reader can confirm
        the prev came from the previous round's emitted fraction, not
        the schedule).

    Returns
    -------
    FactorValue
        ``FactorValue(bounded_merge(...))``.

    Raises
    ------
    MergeAuthorityError
        When ``prev`` is ``None`` and ``audit_codes`` is supplied
        (``ERR_PREV_REQUIRED`` is appended to ``audit_codes`` before
        the error is raised); also raised on any underlying bounded
        merge validation failure.
    """
    delta_up, delta_down = _delta_caps_for_channel(delta_caps_by_channel, channel)
    cap = _cap_for_channel(schedule_sample)
    floor = _floor_for_channel(
        fresh_noise_floor,
        fresh_noise_floor_by_channel,
        schedule_sample,
        channel,
        audit_codes=audit_codes,
    )
    if prev is None:
        if audit_codes is not None:
            audit_codes.append(ERR_PREV_REQUIRED)
        raise MergeAuthorityError(
            "prev is required for orchestrator-driven merge; "
            "the schedule value is the cap, not the prev"
        )
    prev_v = _coerce_finite_real(prev, name="prev")
    if audit_codes is not None:
        audit_codes.append(MERGE_PREV_ANCHORED_TO_LAST_EMITTED)

    merged = bounded_merge(
        prev=prev_v,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_up,
        delta_cap_down=delta_down,
        audit_codes=audit_codes,
    )
    return FactorValue(float(merged))
