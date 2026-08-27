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
* The bounded merge is delegated to the algorithm-layer
  :class:`~adaptive_reflow.algorithm.BoundedMergeOperator` via
  :func:`~adaptive_reflow.algorithm.default_bounded_merge_operator`;
  this module is the legacy public entry point and stays bit-compatible
  with the original signature so existing callers (and existing tests)
  continue to work unchanged.

Tasks satisfied:

* ``DTB-R3`` — replace the only-increase dynamic-control merge; bounded
  both up and down by per-round delta caps and a fresh-noise floor.

Public surface:

* :data:`MERGE_AUTHORITY_SCHEMA_NAME`
* :data:`MERGE_AUTHORITY_SCHEMA_VERSION`
* :func:`bounded_merge` — thin wrapper around
  :meth:`~adaptive_reflow.algorithm.BoundedMergeOperator.merge`.
* :func:`bounded_merge_with_schedule` — orchestrator-level helper that
  wires the bounded merge to a :class:`CosineScheduleSample` and a
  per-channel delta-cap mapping.
* Re-exports of the algorithm-layer operator types for back-compat:
  :class:`MergeOperatorProtocol`, :class:`BoundedMergeOperator`,
  :class:`MergeAuthorityError`, and the canonical audit / error codes.

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

from adaptive_reflow.algorithm import (
    ERR_PREV_REQUIRED as _ERR_PREV_REQUIRED,
)
from adaptive_reflow.algorithm import (
    MERGE_DEGENERATE_INTERVAL as _MERGE_DEGENERATE_INTERVAL,
)
from adaptive_reflow.algorithm import (
    MERGE_FLOOR_FALLBACK as _MERGE_FLOOR_FALLBACK,
)
from adaptive_reflow.algorithm import (
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED as _MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
)
from adaptive_reflow.algorithm import (
    BoundedMergeOperator as _BoundedMergeOperator,
)
from adaptive_reflow.algorithm import (
    MergeAuthorityError as _MergeAuthorityError,
)
from adaptive_reflow.algorithm import (
    MergeOperatorProtocol as _MergeOperatorProtocol,
)
from adaptive_reflow.algorithm import (
    default_bounded_merge_operator as _default_bounded_merge_operator,
)
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
    "BoundedMergeOperator",
    "MergeAuthorityError",
    "MergeOperatorProtocol",
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

# Re-export the algorithm-layer constants under their historical names
# so existing callers (and tests) that import them from
# ``adaptive_reflow.frame`` keep working.
ERR_PREV_REQUIRED: str = _ERR_PREV_REQUIRED
MERGE_DEGENERATE_INTERVAL: str = _MERGE_DEGENERATE_INTERVAL
MERGE_FLOOR_FALLBACK: str = _MERGE_FLOOR_FALLBACK
MERGE_PREV_ANCHORED_TO_LAST_EMITTED: str = _MERGE_PREV_ANCHORED_TO_LAST_EMITTED
MergeAuthorityError = _MergeAuthorityError
MergeOperatorProtocol = _MergeOperatorProtocol
BoundedMergeOperator = _BoundedMergeOperator


# ---------------------------------------------------------------------------
# Internal coercion helpers (kept here so bounded_merge_with_schedule
# stays self-contained; the operator's own helper is private).
# ---------------------------------------------------------------------------


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
# Bounded merge (thin wrapper around the canonical operator)
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

    This function is the legacy public entry point and a thin wrapper
    around
    :meth:`adaptive_reflow.algorithm.BoundedMergeOperator.merge`. It
    exists for back-compat with callers (and tests) that pre-date the
    algorithm-layer :class:`MergeOperatorProtocol` abstraction; new
    callers should instantiate :class:`BoundedMergeOperator` directly.

    See :class:`BoundedMergeOperator` for the full semantic
    specification (cap / floor / delta-cap envelope, degenerate-interval
    collapse to the floor, audit-code emission).
    """
    return _default_bounded_merge_operator().merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
        audit_codes=audit_codes,
    )


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
    from adaptive_reflow.algorithm.merge_operator import _coerce_finite_real

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
