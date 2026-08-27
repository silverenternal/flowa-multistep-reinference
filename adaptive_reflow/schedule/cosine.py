"""Cosine-annealed outer restart-noise budget (DTB-NA1).

This module satisfies ``DTB-NA1`` by exposing the **closed schedule family**
used to allocate fresh-noise capacity to the outer re-inference cycle. The
schedule is a *capacity* source; the channel rule (``channel_rule.py``) is
the only component allowed to derive ``beta`` from it. This module never
imports ``torch`` and never writes a ``beta`` value.

Public surface:

* :func:`n_cap_for_round` — closed-form capacity function. Pure, deterministic.
* :func:`memory_fraction_from_schedule` — translate a schedule sample into
  the per-round memory fraction ``m = 1 - n_cap`` consumed by the engine
  and the universal ``apply_restart_distribution`` boundary.
* :class:`CosineScheduleSampler` — records a fresh :class:`CosineScheduleSample`
  and a :class:`RestartTriggerEvent` when an outer cycle restarts.
* :func:`validate_cosine_schedule_config` — deterministic config validator.
* :func:`default_floor_by_channel` — read-only view of the per-channel floors.

Schedule family is closed: ``constant``, ``linear``, ``cosine_no_restart``,
and ``cosine_guarded_restart``. The ``empirical_learned`` slot is reserved
for a future calibrated schedule and explicitly raises
:exc:`NotImplementedError`. Guarded restart is detected by sampling over
the schedule; this module only supplies capacity, not the restart trigger.

Tasks satisfied:

* ``DTB-NA1`` — cosine annealed outer restart-noise budget (capacity only).
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, cast

from adaptive_reflow.contracts import (
    CHANNEL_NAMES,
    RESTART_TRIGGER_CODES,
    SCHEDULE_FAMILIES,
    ArtifactHash,
    BundleId,
    ChannelName,
    CosineScheduleConfig,
    CosineScheduleSample,
    FactorValue,
    ProvenanceChain,
    RestartTriggerCode,
    RestartTriggerEvent,
    TriggerId,
    hash_artifact,
)

# The diagnostic-ledger module is intentionally imported with a deferred,
# failure-tolerant wrapper. The ledger is *diagnostic only* (DTB-L4) and
# MUST NOT influence the schedule computation. If the module is unavailable
# (e.g. partial checkout, partial install), the schedule logic still works;
# the diagnostic hook degrades to a no-op.
FreshNoiseCumulativeMassRecord: Any
try:  # pragma: no cover - import-time branching
    from adaptive_reflow.diagnostics.ledger import FreshNoiseCumulativeMassRecord
except Exception:  # noqa: BLE001
    FreshNoiseCumulativeMassRecord = None


# ---------------------------------------------------------------------------
# Canonical blocker / error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_CYCLE_LENGTH_NON_INT = "cycle_length_must_be_int"
ERR_CYCLE_LENGTH_TOO_SMALL = "cycle_length_must_be_at_least_1"
ERR_SCHEDULE_FAMILY_INVALID = "schedule_family_invalid"
ERR_N_MIN_NOT_FINITE = "n_min_not_finite"
ERR_N_MAX_NOT_FINITE = "n_max_not_finite"
ERR_N_MIN_OUT_OF_RANGE = "n_min_out_of_unit_interval"
ERR_N_MAX_OUT_OF_RANGE = "n_max_out_of_unit_interval"
ERR_N_MAX_LT_N_MIN = "n_max_must_be_at_least_n_min"
ERR_PER_CHANNEL_CAP_INVALID = "per_channel_caps_invalid"
ERR_FRESH_NOISE_FLOOR_INVALID = "fresh_noise_floor_by_channel_invalid"
ERR_DELTA_CAP_INVALID = "symmetric_delta_caps_by_channel_invalid"
ERR_UNKNOWN_CHANNEL = "channel_not_in_canonical_set"
ERR_RESTART_TRIGGER_INVALID = "restart_triggers_allowed_invalid"
ERR_CONFIG_HASH_EMPTY = "config_hash_must_be_non_empty"
ERR_NOT_FROZEN_BEFORE_EVAL = "frozen_before_evaluation_must_be_true"


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _coerce_factor_value(x: object) -> float:
    """Coerce ``x`` to a Python ``float`` (booleans become 0/1)."""
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise TypeError(f"expected a real number, got {type(x).__name__}")
    return float(x)


def _clip_unit_finite(x: float) -> float:
    """Clip ``x`` to ``[0, 1]`` and refuse non-finite values."""
    if not math.isfinite(x):
        raise ValueError(f"schedule capacity must be finite, got {x!r}")
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _coerce_int_nonneg(x: object, name: str) -> int:
    """Coerce ``x`` to a non-negative ``int`` or raise :exc:`ValueError`."""
    if isinstance(x, bool) or not isinstance(x, int):
        raise ValueError(f"{name} must be int, got {x!r}")
    if int(x) < 0:
        raise ValueError(f"{name} must be >= 0, got {x}")
    return int(x)


def _is_unit_factor(x: object) -> tuple[bool, str | None]:
    """Return ``(ok, message_or_None)`` for a value claimed to be a unit factor."""
    if isinstance(x, bool):
        # Booleans are not valid unit factors: they encode a different type
        # but pass arithmetic checks. Surface them explicitly.
        return (False, "boolean is not a unit factor")
    if not isinstance(x, (int, float)):
        return (False, f"not a real number, got {type(x).__name__}")
    f = float(x)
    if not math.isfinite(f):
        return (False, f"not finite, got {f!r}")
    if f < 0.0 or f > 1.0:
        return (False, f"out of [0, 1], got {f!r}")
    return (True, None)


# ---------------------------------------------------------------------------
# Pure capacity function (closed schedule family)
# ---------------------------------------------------------------------------


def n_cap_for_round(
    config: CosineScheduleConfig,
    round_in_cycle: int,
) -> FactorValue:
    """Compute the closed-form fresh-noise capacity for ``round_in_cycle``.

    Pure function. The closed schedule family covers ``constant``, ``linear``,
    ``cosine_no_restart``, and ``cosine_guarded_restart``. The
    ``empirical_learned`` slot is reserved for a future calibrated schedule
    and raises :exc:`NotImplementedError`. Guarded restart is detected by
    sampling over the schedule; this function only supplies capacity, not
    the restart trigger.

    The closed-form cosine is:

        n_cap = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2
        u_r = r / (L - 1)

    with the deterministic edge case ``L == 1 -> n_max`` and the linear
    family ``n_cap = n_max - (n_max - n_min) * u_r``.

    Raises:
        ValueError: ``cycle_length < 1``; ``round_in_cycle`` outside
            ``[0, cycle_length - 1]`` when ``cycle_length > 1``; or an
            unrecognized ``schedule_family``.
        NotImplementedError: ``schedule_family == 'empirical_learned'`` —
            reserved for a future calibrated schedule per ``todo.json``.
    """
    # 1. cycle_length must be int >= 1.
    if isinstance(config.cycle_length, bool) or not isinstance(config.cycle_length, int):
        raise ValueError(
            f"cycle_length must be int >= 1, got {config.cycle_length!r}"
        )
    L = int(config.cycle_length)
    if L < 1:
        raise ValueError(f"cycle_length must be >= 1, got {L}")

    # 2. round_in_cycle must be int.
    if isinstance(round_in_cycle, bool) or not isinstance(round_in_cycle, int):
        raise ValueError(
            f"round_in_cycle must be int, got {round_in_cycle!r}"
        )
    r = int(round_in_cycle)

    # 3. n_min / n_max coercion — fail loudly if malformed. Caller is
    #    expected to have validated, but the safety net catches drift.
    n_min = _coerce_factor_value(config.n_min)
    n_max = _coerce_factor_value(config.n_max)

    # 4. L == 1: deterministic edge case, return n_max regardless of family.
    if L == 1:
        return FactorValue(_clip_unit_finite(n_max))

    # 5. Family must be one of the canonical literals.
    family = config.schedule_family
    if family not in SCHEDULE_FAMILIES:
        raise ValueError(
            f"schedule_family must be one of {SCHEDULE_FAMILIES!r}, got {family!r}"
        )

    # 6. empirical_learned is reserved for a future calibrated schedule.
    if family == "empirical_learned":
        raise NotImplementedError(
            "empirical_learned schedule is reserved for future calibrated "
            "schedules per todo.json (DTB-NA1); it is not yet supported by "
            "n_cap_for_round. The slot may never bypass fresh_noise_floor "
            "or any channel gate, even after calibration."
        )

    # 7. r must be in [0, L-1] for cycle_length > 1.
    if r < 0 or r > L - 1:
        raise ValueError(
            f"round_in_cycle must be in [0, {L - 1}] for cycle_length={L}, got {r}"
        )

    u_r = r / (L - 1)

    # 8. Closed-form dispatch.
    if family == "constant":
        n_cap = n_max
    elif family == "linear":
        n_cap = n_max - (n_max - n_min) * u_r
    elif family in ("cosine_no_restart", "cosine_guarded_restart"):
        n_cap = n_min + (n_max - n_min) * (1.0 + math.cos(math.pi * u_r)) / 2.0
    else:
        # Defensive: should be unreachable given the SCHEDULE_FAMILIES check.
        raise ValueError(f"unrecognized schedule_family: {family!r}")

    # 9. Clip to [0, 1] and require finite (defensive against roundoff).
    return FactorValue(_clip_unit_finite(n_cap))


# ---------------------------------------------------------------------------
# Memory fraction (per-round, derived from the schedule)
# ---------------------------------------------------------------------------


def memory_fraction_from_schedule(
    schedule_sample: CosineScheduleSample,
) -> float:
    """Return the per-round memory fraction derived from ``schedule_sample``.

    The per-round memory fraction is the share of the prior endpoint that
    should be retained when restarting at ``schedule_sample.round_in_cycle``.
    It is the natural complement of the schedule's fresh-noise capacity:

        memory_fraction = 1.0 - n_cap

    so at round 0 with ``n_cap = n_max`` (large), the memory fraction is
    small (lots of fresh noise for exploration); at round L-1 with
    ``n_cap = n_min`` (small), the memory fraction is large (preserve
    the prior and refine). For a "coarse to fine" drug-design
    intuition this matches the annealed restart schedule.

    The complement relationship is the canonical wiring the framework
    exposes to the universal :class:`FlowMatchingODEAdapter` boundary
    (see :func:`adaptive_reflow.frame.engine.Engine.run_round`,
    ADR-0010). The helper is pure: identical inputs always yield
    identical outputs; the result is clipped to ``[0, 1]`` and
    refuses non-finite or non-numeric ``n_cap`` inputs.

    Parameters
    ----------
    schedule_sample:
        A :class:`CosineScheduleSample` produced by
        :func:`n_cap_for_round` (directly or via
        :class:`CosineScheduleSampler`).

    Returns
    -------
    float
        The per-round memory fraction in ``[0, 1]``.

    Raises
    ------
    ValueError
        On a ``None`` ``schedule_sample``, a non-numeric ``n_cap``, or a
        non-finite ``n_cap``.
    """
    if schedule_sample is None:
        raise ValueError("schedule_sample must not be None")
    n_cap_raw = schedule_sample.n_cap
    if isinstance(n_cap_raw, bool) or not isinstance(n_cap_raw, (int, float)):
        raise ValueError(
            f"schedule_sample.n_cap must be a real number, got "
            f"{type(n_cap_raw).__name__}"
        )
    n_cap = float(n_cap_raw)
    if not math.isfinite(n_cap):
        raise ValueError(f"schedule_sample.n_cap must be finite, got {n_cap!r}")
    return float(max(0.0, min(1.0, 1.0 - n_cap)))


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_cosine_schedule_config(
    config: CosineScheduleConfig,
) -> tuple[str, ...]:
    """Validate :class:`CosineScheduleConfig` and return a tuple of error codes.

    The returned tuple is empty when ``config`` is valid; otherwise it
    contains deterministic, ASCII-only error codes that callers can use as
    ledger blockers or assertion messages.

    The validator covers:

    * ``cycle_length`` is ``int >= 1``
    * ``schedule_family`` is in the canonical literal set
    * ``n_min``, ``n_max`` are finite, in ``[0, 1]``, and ``n_max >= n_min``
    * per-channel caps / floors / delta caps are finite values in ``[0, 1]``
      keyed by a canonical channel name
    * ``restart_triggers_allowed`` is a tuple of canonical restart codes
    * ``config_hash`` is non-empty
    * ``frozen_before_evaluation`` is ``True`` (per CONTRACTS.md §4)
    """
    errors: list[str] = []

    # cycle_length
    if isinstance(config.cycle_length, bool) or not isinstance(config.cycle_length, int):
        errors.append(ERR_CYCLE_LENGTH_NON_INT)
    elif int(config.cycle_length) < 1:
        errors.append(ERR_CYCLE_LENGTH_TOO_SMALL)

    # schedule_family
    if config.schedule_family not in SCHEDULE_FAMILIES:
        errors.append(ERR_SCHEDULE_FAMILY_INVALID)

    # n_min, n_max
    n_min_ok = True
    n_max_ok = True
    n_min_val: float | None = None
    n_max_val: float | None = None
    try:
        n_min_val = _coerce_factor_value(config.n_min)
        if not math.isfinite(n_min_val):
            errors.append(ERR_N_MIN_NOT_FINITE)
            n_min_ok = False
        elif n_min_val < 0.0 or n_min_val > 1.0:
            errors.append(ERR_N_MIN_OUT_OF_RANGE)
            n_min_ok = False
    except (TypeError, ValueError):
        errors.append(ERR_N_MIN_NOT_FINITE)
        n_min_ok = False
    try:
        n_max_val = _coerce_factor_value(config.n_max)
        if not math.isfinite(n_max_val):
            errors.append(ERR_N_MAX_NOT_FINITE)
            n_max_ok = False
        elif n_max_val < 0.0 or n_max_val > 1.0:
            errors.append(ERR_N_MAX_OUT_OF_RANGE)
            n_max_ok = False
    except (TypeError, ValueError):
        errors.append(ERR_N_MAX_NOT_FINITE)
        n_max_ok = False
    if n_min_ok and n_max_ok and n_min_val is not None and n_max_val is not None and n_max_val < n_min_val:
        errors.append(ERR_N_MAX_LT_N_MIN)

    # per-channel mapping fields
    for label, mapping in (
        ("per_channel_caps", config.per_channel_caps),
        ("fresh_noise_floor_by_channel", config.fresh_noise_floor_by_channel),
        ("symmetric_delta_caps_by_channel", config.symmetric_delta_caps_by_channel),
    ):
        if mapping is None:
            errors.append(f"{label}_missing")
            continue
        if not isinstance(mapping, Mapping):
            errors.append(f"{label}_not_a_mapping")
            continue
        for channel, value in mapping.items():
            if channel not in CHANNEL_NAMES:
                errors.append(f"{ERR_UNKNOWN_CHANNEL}:{label}:{channel}")
            ok, msg = _is_unit_factor(value)
            if not ok:
                errors.append(f"{label}:{channel}:{msg}")

    # restart_triggers_allowed
    if not isinstance(config.restart_triggers_allowed, tuple):
        errors.append("restart_triggers_allowed_not_a_tuple")
    else:
        for code in config.restart_triggers_allowed:
            if code not in RESTART_TRIGGER_CODES:
                errors.append(f"{ERR_RESTART_TRIGGER_INVALID}:{code}")

    # config_hash
    if not config.config_hash:
        errors.append(ERR_CONFIG_HASH_EMPTY)

    # frozen_before_evaluation
    if not config.frozen_before_evaluation:
        errors.append(ERR_NOT_FROZEN_BEFORE_EVAL)

    return tuple(errors)


def default_floor_by_channel(
    config: CosineScheduleConfig,
) -> Mapping[ChannelName, FactorValue]:
    """Return a read-only mapping of the configured per-channel fresh-noise floors.

    Iterates over the canonical :data:`CHANNEL_NAMES` set so the output keys
    are deterministic. Channels that are missing from
    ``config.fresh_noise_floor_by_channel`` are silently omitted; channels
    carrying non-finite or out-of-range values are also omitted so the
    helper never raises on a partially-bad config (the validator is the
    authoritative gate).
    """
    floors: dict[ChannelName, FactorValue] = {}
    raw = config.fresh_noise_floor_by_channel
    if isinstance(raw, Mapping):
        for channel in CHANNEL_NAMES:
            if channel not in raw:
                continue
            try:
                v = _coerce_factor_value(raw[cast(ChannelName, channel)])
            except (TypeError, ValueError):
                continue
            try:
                floors[ChannelName(str(channel))] = FactorValue(_clip_unit_finite(v))
            except ValueError:
                continue
    return MappingProxyType(floors)


# ---------------------------------------------------------------------------
# Stateful sampler
# ---------------------------------------------------------------------------


class CosineScheduleSampler:
    """Deprecated stateful sampler — thin shim over
    :class:`adaptive_reflow.algorithm.CosineAnnealScheduler`.

    .. deprecated::
        The algorithm layer is now abstract: depend on
        :class:`adaptive_reflow.algorithm.SchedulerProtocol` and construct a
        concrete scheduler (``default_cosine_scheduler()`` for the cosine
        default). This class is retained so existing
        ``from adaptive_reflow.schedule.cosine import CosineScheduleSampler``
        imports keep working; instantiating it emits a
        :exc:`DeprecationWarning`. It delegates all capacity computation to
        :class:`~adaptive_reflow.algorithm.CosineAnnealScheduler` and keeps
        the restart-event surface unchanged.

    The sampler is a thin facade over :func:`n_cap_for_round` plus a cache of
    the most recent sample. The cache is consulted by
    :meth:`compute_restart_event` (and the legacy
    :meth:`restart_trigger_event` wrapper) to derive the *before* capacity
    without requiring the caller to thread the previous round's n_cap
    through the call site. The sampler never writes a ``beta`` value — the
    channel rule is the only consumer allowed to translate capacity into
    ``beta``.

    Invariants:

    * ``self.last_sample`` is the most recent :class:`CosineScheduleSample`
      emitted by :meth:`sample` or committed via
      :meth:`record_restart_event`. It is ``None`` until the first sample
      is taken.
    * :meth:`compute_restart_event` is **pure** w.r.t. ``self._last_sample``:
      it reads ``self._last_sample`` for ``noise_capacity_before`` and
      computes a fresh after-sample internally, but does NOT mutate the
      cache. Two consecutive ``compute_restart_event`` calls with identical
      arguments see the same ``self._last_sample`` value (BEFORE state on
      both calls).
    * :meth:`record_restart_event` commits the after-sample embedded in a
      previously-computed event to ``self._last_sample``. It is idempotent:
      calling it twice with the same event leaves ``self._last_sample``
      equal to the embedded sample both times.
    * The sampler never mutates ``config``; it is a frozen dataclass.
    """

    def __init__(self, config: CosineScheduleConfig) -> None:
        warnings.warn(
            "CosineScheduleSampler is deprecated; use "
            "adaptive_reflow.algorithm.CosineAnnealScheduler (or "
            "default_cosine_scheduler()) behind SchedulerProtocol instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Deferred import: adaptive_reflow.algorithm.scheduler imports this
        # module for n_cap_for_round / memory_fraction_from_schedule, so the
        # dependency must only be resolved at call time.
        from adaptive_reflow.algorithm.scheduler import CosineAnnealScheduler

        self._config = config
        self._scheduler = CosineAnnealScheduler(config)
        self._last_sample: CosineScheduleSample | None = None

    @property
    def config(self) -> CosineScheduleConfig:
        """Return the :class:`CosineScheduleConfig` the sampler was built from."""
        return self._config

    @property
    def last_sample(self) -> CosineScheduleSample | None:
        """Return the most recent sample, or ``None`` if none has been taken."""
        return self._last_sample

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> CosineScheduleSample:
        """Record a fresh :class:`CosineScheduleSample`.

        ``u_r`` is computed as ``round_in_cycle / max(L - 1, 1)`` so that
        ``L == 1`` returns ``1.0`` rather than ``0`` (deterministic edge
        case; the capacity is taken from :func:`n_cap_for_round` which
        returns ``n_max`` for ``L == 1``). The sample's
        :attr:`CosineScheduleSample.computed_at_round` is set to
        ``target_round`` so the schedule round can be cross-referenced with
        the engine target round.
        """
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        # round_in_cycle coercion is delegated to n_cap_for_round, which
        # also enforces the cycle-length range.

        sample = self._scheduler.sample(
            outer_cycle_id, round_in_cycle, target_round
        ).as_cosine_schedule_sample()
        self._last_sample = sample
        return sample

    def restart_trigger_event(
        self,
        trigger_code: RestartTriggerCode,
        outer_cycle_id_old: int,
        outer_cycle_id_new: int,
        discarded_bundle_ids: tuple[BundleId, ...],
        trigger_metric_snapshot: Mapping[str, float],
        unresolved_metric_deficit: Mapping[str, float],
        *,
        target_round: int | None = None,
        recorded_at_round: int | None = None,
        provenance: ProvenanceChain | None = None,
    ) -> RestartTriggerEvent:
        """Back-compat wrapper around :meth:`compute_restart_event` +
        :meth:`record_restart_event`.

        .. deprecated::
            This convenience wrapper is retained for backward compatibility
            only. New code should call :meth:`compute_restart_event` (pure)
            first, then :meth:`record_restart_event` (mutation) explicitly,
            so the mutating boundary is visible at the call site. The
            wrapper hides the split, which is exactly the algorithmic gap
            (B1) the split was introduced to expose.

        Behaviorally equivalent to the pre-split single call: it builds
        the event via :meth:`compute_restart_event` and commits the
        embedded after-sample to ``self._last_sample`` via
        :meth:`record_restart_event` before returning the event.

        See :meth:`compute_restart_event` for argument and validation
        semantics.
        """
        event = self.compute_restart_event(
            trigger_code,
            outer_cycle_id_old,
            outer_cycle_id_new,
            discarded_bundle_ids,
            trigger_metric_snapshot,
            unresolved_metric_deficit,
            target_round=target_round,
            recorded_at_round=recorded_at_round,
            provenance=provenance,
        )
        self.record_restart_event(event)
        return event

    def compute_restart_event(
        self,
        trigger_code: RestartTriggerCode,
        outer_cycle_id_old: int,
        outer_cycle_id_new: int,
        discarded_bundle_ids: tuple[BundleId, ...],
        trigger_metric_snapshot: Mapping[str, float],
        unresolved_metric_deficit: Mapping[str, float],
        *,
        target_round: int | None = None,
        recorded_at_round: int | None = None,
        provenance: ProvenanceChain | None = None,
    ) -> RestartTriggerEvent:
        """Build a :class:`RestartTriggerEvent` WITHOUT mutating
        ``self._last_sample`` (B1 fix: purity boundary).

        ``noise_capacity_before`` is taken from the most recent
        :meth:`sample` call (or ``config.n_max`` if no sample was taken
        yet). ``noise_capacity_after`` is taken by sampling at the start
        of the new cycle — ``(outer_cycle_id_new, round_in_cycle=0)``,
        which yields ``n_max`` for every closed-form family — **but the
        sample is NOT cached on the sampler**. The after-sample is
        embedded as a private ``_after_sample`` attribute on the returned
        event so that :meth:`record_restart_event` can commit it later.

        Two consecutive ``compute_restart_event`` calls with identical
        arguments therefore see the same ``self._last_sample`` value
        (BEFORE state on both calls). This is the gap B1 fix: callers can
        now reason about the schedule without the sampler silently
        rewinding its own baseline.

        ``recorded_at_round`` defaults to ``target_round``, which itself
        defaults to the most recent sample's ``computed_at_round`` (or
        ``0`` if no sample was taken).

        The ``provenance`` argument is optional and defaults to an empty
        :data:`ProvenanceChain`; the caller is expected to thread a
        non-empty chain before downstream validation.

        Raises:
            ValueError: ``trigger_code`` is not in
                :data:`RESTART_TRIGGER_CODES`, or ``outer_cycle_id_old/new``
                is not a non-negative ``int``.
        """
        # Validate cycle ids and trigger code.
        outer_cycle_id_old = _coerce_int_nonneg(
            outer_cycle_id_old, "outer_cycle_id_old"
        )
        outer_cycle_id_new = _coerce_int_nonneg(
            outer_cycle_id_new, "outer_cycle_id_new"
        )
        if trigger_code not in RESTART_TRIGGER_CODES:
            raise ValueError(
                f"trigger_code must be one of {RESTART_TRIGGER_CODES!r}, "
                f"got {trigger_code!r}"
            )

        # Resolve target_round: prefer explicit kwarg, else cached sample.
        if target_round is None:
            if self._last_sample is not None:
                target_round = int(self._last_sample.computed_at_round)
            else:
                target_round = 0
        else:
            target_round = _coerce_int_nonneg(target_round, "target_round")

        # noise_capacity_before: from cached last sample (READ-ONLY), or
        # n_max fallback. We deliberately do NOT mutate self._last_sample.
        if self._last_sample is not None:
            noise_capacity_before = self._last_sample.n_cap
        else:
            noise_capacity_before = FactorValue(
                _clip_unit_finite(_coerce_factor_value(self._config.n_max))
            )

        # noise_capacity_after: sample at (cycle_new, 0, target_round) but
        # DO NOT cache the sample on the sampler.
        after_sample = self._build_sample_without_cache(
            outer_cycle_id_new, 0, target_round
        )
        noise_capacity_after = after_sample.n_cap

        # recorded_at_round: prefer explicit kwarg, else target_round.
        if recorded_at_round is None:
            recorded_at_round = target_round
        else:
            recorded_at_round = _coerce_int_nonneg(
                recorded_at_round, "recorded_at_round"
            )

        # Coerce discarded_bundle_ids to tuple.
        if not isinstance(discarded_bundle_ids, tuple):
            discarded_bundle_ids = tuple(discarded_bundle_ids)

        trigger_id = TriggerId(
            hash_artifact(
                {
                    "trigger_code": str(trigger_code),
                    "outer_cycle_id_old": int(outer_cycle_id_old),
                    "outer_cycle_id_new": int(outer_cycle_id_new),
                    "recorded_at_round": int(recorded_at_round),
                    "discarded_source_bundle_ids": [
                        str(b) for b in discarded_bundle_ids
                    ],
                }
            )
        )

        event = RestartTriggerEvent(
            trigger_id=trigger_id,
            outer_cycle_id_old=outer_cycle_id_old,
            outer_cycle_id_new=outer_cycle_id_new,
            trigger_code=trigger_code,
            trigger_metric_snapshot=dict(trigger_metric_snapshot),
            discarded_source_bundle_ids=discarded_bundle_ids,
            noise_capacity_before=noise_capacity_before,
            noise_capacity_after=noise_capacity_after,
            unresolved_metric_deficit=dict(unresolved_metric_deficit),
            provenance=(
                provenance
                if provenance is not None
                else ProvenanceChain(())
            ),
            recorded_at_round=recorded_at_round,
        )
        # Embed the after-sample as a private attribute on the event so
        # :meth:`record_restart_event` can commit it later. The dataclass
        # is frozen, so we bypass the freeze via object.__setattr__; this
        # does not affect equality or hash of the event (the public
        # fields are unchanged).
        object.__setattr__(event, "_after_sample", after_sample)
        return event

    def _build_sample_without_cache(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> CosineScheduleSample:
        """Build a :class:`CosineScheduleSample` without writing
        ``self._last_sample``.

        Mirrors the construction in :meth:`sample` but does not mutate
        the sampler's cache. Used by :meth:`compute_restart_event` to
        derive ``noise_capacity_after` for a fresh cycle while
        preserving the *before* baseline for the caller.
        """
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")

        # The delegate caches its own last sample; the legacy sampler's
        # ``self._last_sample`` is deliberately left untouched here (B1).
        return self._scheduler.sample(
            outer_cycle_id, round_in_cycle, target_round
        ).as_cosine_schedule_sample()

    def record_restart_event(self, event: RestartTriggerEvent) -> None:
        """Commit the after-sample embedded in ``event`` to
        ``self._last_sample`` (B1 fix: explicit mutation boundary).

        The event MUST have been produced by :meth:`compute_restart_event`
        (or the legacy :meth:`restart_trigger_event` wrapper); it carries
        the after-sample as a private ``_after_sample`` attribute. If the
        attribute is missing, the event did not originate from the
        scheduler and the call is rejected so a stray caller cannot
        silently overwrite ``self._last_sample`` with a bogus value.

        Idempotent w.r.t. ``event``: calling this method twice with the
        same event leaves ``self._last_sample`` equal to the embedded
        sample both times. The after-sample object is preserved across
        calls, so ``self._last_sample is event._after_sample`` holds
        before and after a no-op repeat.

        Raises:
            ValueError: ``event`` does not carry an ``_after_sample``
                attribute (i.e. it was not produced by
                :meth:`compute_restart_event`).
        """
        after_sample = getattr(event, "_after_sample", None)
        if after_sample is None:
            raise ValueError(
                "RestartTriggerEvent was not produced by "
                "CosineScheduleSampler.compute_restart_event; missing "
                "_after_sample attribute. Refusing to mutate "
                "self._last_sample with an untrusted event."
            )
        self._last_sample = after_sample


# ---------------------------------------------------------------------------
# Diagnostic ledger hook (DTB-L4)
# ---------------------------------------------------------------------------
#
# The functions below are PURE ADDITIVE hooks for the diagnostic ledger. They
# NEVER write a ``beta``, NEVER prune candidates, and NEVER relax any claim
# gate. They exist only to emit per-round
# :class:`FreshNoiseCumulativeMassRecord` rows into a returnable diagnostics
# dict so downstream auditors can reconstruct the cumulative-mass curve.
#
# The schedule computation path (``:func:`n_cap_for_round`` and
# :class:`CosineScheduleSampler`) is unchanged; this section only adds
# read-only observers.


def _capacity_curve_for_cycle(
    config: CosineScheduleConfig,
    outer_cycle_id: int,
) -> tuple[tuple[int, float], ...]:
    """Compute the full per-round capacity curve for one outer cycle.

    The curve is a tuple of ``(round_in_cycle, n_cap)`` pairs and is
    deterministic; it depends only on the frozen config and the cycle id.
    This helper does not modify ``config`` and does not invoke any
    stateful sampler.
    """
    L = int(config.cycle_length)
    if L < 1:
        return ()
    rounds: list[tuple[int, float]] = []
    for r in range(L):
        n_cap = n_cap_for_round(config, r)
        rounds.append((int(r), float(n_cap)))
    return tuple(rounds)


def build_fresh_noise_diagnostics(
    config: CosineScheduleConfig,
    outer_cycle_id: int,
) -> dict[str, Any]:
    """Build a returnable diagnostics dict for the cycle (DTB-L4 hook).

    The returned dict has the shape::

        {
            "outer_cycle_id": <int>,
            "schedule_family": <str>,
            "n_min": <float>,
            "n_max": <float>,
            "cycle_length": <int>,
            "per_round_records": {
                <round_in_cycle>: FreshNoiseCumulativeMassRecord, ...
            },
            "cumulative_mass_curve": tuple[float, ...],
            "ledger_only": True,
            "schema_version": "adaptive_reflow_fresh_noise_diagnostics_v1",
        }

    Each :class:`FreshNoiseCumulativeMassRecord` carries the same fields as
    :func:`diagnostic_ledger.validate_fresh_noise_cumulative_mass_record`
    expects, plus a frozen ``capacity_curve`` field that mirrors the full
    cycle curve so downstream auditors can recompute the cumulative mass.

    The hook is **purely observational**: it never returns a beta, never
    prunes candidates, and never asserts a claim. The ``ledger_only`` flag
    is set to ``True`` at the dict level so consumers can pattern-match on
    it.

    When :class:`FreshNoiseCumulativeMassRecord` is unavailable (deferred
    import failure), the hook still returns the same dict shape with
    ``per_round_records`` replaced by ``"unavailable"`` and the cumulative
    mass curve as plain ``float`` values; the dict remains
    ``ledger_only=True``.
    """
    L = int(config.cycle_length)
    n_min_val = float(_coerce_factor_value(config.n_min))
    n_max_val = float(_coerce_factor_value(config.n_max))
    curve = _capacity_curve_for_cycle(config, int(outer_cycle_id))
    cumulative: list[float] = []
    running = 0.0
    for _r, n in curve:
        running += float(n)
        cumulative.append(running)
    cumulative_tuple = tuple(cumulative)

    per_round_records: Any = "unavailable"
    if FreshNoiseCumulativeMassRecord is not None:
        per_round_records = {}
        for (r, n), cum in zip(curve, cumulative_tuple, strict=False):
            per_round_records[int(r)] = FreshNoiseCumulativeMassRecord(
                cycle_id=int(outer_cycle_id),
                round_in_cycle=int(r),
                n_cap=float(n),
                n_min=float(n_min_val),
                n_max=float(n_max_val),
                schedule_family=str(config.schedule_family),
                finite_prefix_mass=float(cum),
                capacity_curve=curve,
            )

    return {
        "schema_version": "adaptive_reflow_fresh_noise_diagnostics_v1",
        "outer_cycle_id": int(outer_cycle_id),
        "schedule_family": str(config.schedule_family),
        "n_min": float(n_min_val),
        "n_max": float(n_max_val),
        "cycle_length": int(L),
        "per_round_records": per_round_records,
        "cumulative_mass_curve": cumulative_tuple,
        "ledger_only": True,
    }


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ERR_CONFIG_HASH_EMPTY",
    # Error codes
    "ERR_CYCLE_LENGTH_NON_INT",
    "ERR_CYCLE_LENGTH_TOO_SMALL",
    "ERR_DELTA_CAP_INVALID",
    "ERR_FRESH_NOISE_FLOOR_INVALID",
    "ERR_NOT_FROZEN_BEFORE_EVAL",
    "ERR_N_MAX_LT_N_MIN",
    "ERR_N_MAX_NOT_FINITE",
    "ERR_N_MAX_OUT_OF_RANGE",
    "ERR_N_MIN_NOT_FINITE",
    "ERR_N_MIN_OUT_OF_RANGE",
    "ERR_PER_CHANNEL_CAP_INVALID",
    "ERR_RESTART_TRIGGER_INVALID",
    "ERR_SCHEDULE_FAMILY_INVALID",
    "ERR_UNKNOWN_CHANNEL",
    "CosineScheduleSampler",
    # DTB-L4 diagnostic hook
    "build_fresh_noise_diagnostics",
    "default_floor_by_channel",
    # Public API
    "memory_fraction_from_schedule",
    "n_cap_for_round",
    "validate_cosine_schedule_config",
]
