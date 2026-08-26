"""Diagnostic ledger carriers (DTB-L4).

This module is the **diagnostic-only** leg of DTB-L4. It defines three frozen
dataclasses that record *per-round fresh-noise cumulative mass*, the *spectral
residual band proxy*, and the *tail diagnostic status*. The carriers are
explicitly marked ``ledger_only=True`` and **NEVER influence** the
``beta``/``alpha`` write path, the candidate pruning step, or the claim gate.

The corresponding source of physical / restart / spectral quantities lives in
:mod:`noise_mass_accounting`, which keeps the three quantities
(``physical_noise_proxy``, ``RMS_preserving_mixing_coefficient``,
``exact_spectral_variance``) distinct by construction. Any caller that wants to
*act* on these quantities (e.g. write a new ``beta``) MUST NOT use these
dataclasses: they are observation rows, not control surfaces.

Schedule rows follow the closed cosine / linear / constant families declared in
:mod:`cosine_schedule`. The schedule family string is forwarded as
``schedule_family`` for downstream grouping but is not interpreted.

This module is **stdlib-only**: no ``torch``, no IO, no mutable state. All
fields are immutable; mutating a dataclass raises ````from ``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Canonical blocker / error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_ROUND_NOT_INT = "round_in_cycle_must_be_int"
ERR_ROUND_NEGATIVE = "round_in_cycle_must_be_non_negative"
ERR_CYCLE_NOT_INT = "cycle_id_must_be_int"
ERR_CYCLE_NEGATIVE = "cycle_id_must_be_non_negative"
ERR_N_CAP_NOT_FINITE = "n_cap_must_be_finite"
ERR_N_MIN_NOT_FINITE = "n_min_must_be_finite"
ERR_N_MAX_NOT_FINITE = "n_max_must_be_finite"
ERR_MASS_NOT_FINITE = "finite_prefix_mass_must_be_finite"
ERR_MASS_NEGATIVE = "finite_prefix_mass_must_be_non_negative"
ERR_CAPACITY_CURVE_NOT_TUPLE = "capacity_curve_must_be_tuple_of_pairs"
ERR_CAPACITY_ENTRY_NOT_PAIR = "capacity_curve_entry_must_be_pair"
ERR_RESIDUAL_LOWER_NOT_FINITE = "residual_lower_must_be_finite"
ERR_RESIDUAL_UPPER_NOT_FINITE = "residual_upper_must_be_finite"
ERR_RESIDUAL_ORDER = "residual_lower_must_be_le_residual_upper"
ERR_SUMMABLE_STATUS_INVALID = "summable_stagnation_detected_must_be_bool"


# ---------------------------------------------------------------------------
# Pure helpers (internal)
# ---------------------------------------------------------------------------


def _coerce_finite_float(value: Any, name: str) -> float:
    """Coerce ``value`` to a finite Python ``float``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {type(value).__name__}")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite, got {f!r}")
    return float(f)


def _coerce_nonneg_float(value: Any, name: str) -> float:
    """Coerce ``value`` to a finite, non-negative Python ``float``."""
    f = _coerce_finite_float(value, name)
    if f < 0.0:
        raise ValueError(f"{name} must be non-negative, got {f}")
    return float(f)


def _coerce_int_nonneg(value: Any, name: str) -> int:
    """Coerce ``value`` to a non-negative Python ``int``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be int, got {type(value).__name__}")
    if int(value) < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return int(value)


def _coerce_capacity_curve(
    curve: Any, name: str = "capacity_curve"
) -> tuple[tuple[int, float], ...]:
    """Coerce ``curve`` to a tuple of ``(round, n_cap)`` pairs.

    A capacity_curve is the per-round capacity profile of one outer cycle. Each
    entry is ``(round_in_cycle, n_cap)`` with both fields finite. The curve is
    deterministic; this helper refuses non-finite, non-numeric, or
    malformed entries.
    """
    if curve is None:
        raise ValueError(f"{name} must be a sequence of (round, n_cap) pairs, got None")
    if isinstance(curve, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence of (round, n_cap) pairs, got {type(curve).__name__}")
    if not isinstance(curve, tuple):
        curve = tuple(curve)
    out: list[tuple[int, float]] = []
    for index, entry in enumerate(curve):
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError(
                f"{name}[{index}] must be a (round, n_cap) pair, got {entry!r}"
            )
        r = _coerce_int_nonneg(entry[0], f"{name}[{index}].round")
        n = _coerce_nonneg_float(entry[1], f"{name}[{index}].n_cap")
        out.append((r, n))
    return tuple(out)


# ---------------------------------------------------------------------------
# Diagnostic-only dataclasses
# ---------------------------------------------------------------------------

# All three rows below carry ``ledger_only=True`` as a class-level sentinel
# field. The intent is to make it impossible to silently treat these rows as
# control surfaces. They are observation rows only: NEVER used to derive
# ``beta``, to prune candidates, or to assert a claim.


@dataclass(frozen=True)
class FreshNoiseCumulativeMassRecord:
    """Per-round cumulative-mass ledger row (diagnostic). ``ledger_only=True``.

    A :class:`FreshNoiseCumulativeMassRecord` records the *finite-prefix*
    cumulative mass emitted by one round of the closed schedule family, plus
    the full per-round capacity curve for that cycle so downstream auditors
    can reproduce the sum. The two trailing boolean flags
    (``empirical_only`` and ``finite_prefix_only``) are always ``True`` for
    any row produced by a finite cycle; an honest audit must surface them so
    that future readers cannot confuse the row with a *certified tail
    selection*.

    The default values for ``empirical_only`` and ``finite_prefix_only`` are
    ``True``; passing ``False`` is rejected by the validator. The ledger
    cannot be promoted to a control surface: there is no field that names a
    target channel, a beta write, or a candidate pruning decision.

    NOTE: This dataclass is PURE DIAGNOSTIC. It NEVER influences
    ``beta``/``prune``/``claim`` (``ledger_only=True``).
    """

    cycle_id: int
    round_in_cycle: int
    n_cap: float
    n_min: float
    n_max: float
    schedule_family: str
    finite_prefix_mass: float
    capacity_curve: tuple[tuple[int, float], ...]
    empirical_only: bool = True
    finite_prefix_only: bool = True
    ledger_only: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        # Structural validation: raise ValueError for non-finite floats
        # and malformed capacity_curve. Semantic checks (negatives,
        # empty strings, literal membership) live in the validator
        # function so callers can probe the validator without raising.
        errors: list[str] = []
        for name, value in (
            ("n_cap", self.n_cap),
            ("n_min", self.n_min),
            ("n_max", self.n_max),
            ("finite_prefix_mass", self.finite_prefix_mass),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{name}_not_finite")
                continue
            if not math.isfinite(float(value)):
                errors.append(f"{name}_not_finite")
        # Capacity curve structural shape: each entry must be a 2-tuple
        # of finite (int, float) values.
        if not isinstance(self.capacity_curve, tuple):
            errors.append(ERR_CAPACITY_CURVE_NOT_TUPLE)
        else:
            for index, entry in enumerate(self.capacity_curve):
                if not isinstance(entry, tuple) or len(entry) != 2:
                    errors.append(f"{ERR_CAPACITY_ENTRY_NOT_PAIR}:{index}")
                    continue
                r = entry[0]
                n = entry[1]
                if isinstance(r, bool) or not isinstance(r, int):
                    errors.append(f"capacity_curve:{index}:round_invalid")
                if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(float(n)):
                    errors.append(f"capacity_curve:{index}:n_cap_invalid")
        if errors:
            raise ValueError("; ".join(errors))


@dataclass(frozen=True)
class SpectralResidualBandProxy:
    """Diagnostic spectral residual band proxy. ``ledger_only=True``.

    The residual band is a **diagnostic-only** proxy. It only has authority
    ``diagnostic_only``; the field ``identification_method == "linear_gaussian"``
    is reserved for adapters that provide an explicit linear Gaussian
    identification of the local smoothing operator, and is otherwise ``"none"``.

    The proxy never feeds back into ``beta`` derivation, candidate pruning,
    or the claim gate. A future calibrated authority contract may
    legitimately promote the proxy to ``applicable``, but no current code path
    does so.

    NOTE: This dataclass is PURE DIAGNOSTIC. It NEVER influences
    ``beta``/``prune``/``claim`` (``ledger_only=True``).
    """

    cycle_id: int
    residual_lower: float
    residual_upper: float
    identification_method: Literal["linear_gaussian", "none"] = "none"
    applicability: Literal["applicable", "diagnostic_only"] = "diagnostic_only"
    ledger_only: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        # Structural validation: raise ValueError for non-finite floats.
        # Semantic checks (band order, literal membership) live in the
        # validator function so callers can probe it without raising.
        errors: list[str] = []
        for name, value in (
            ("residual_lower", self.residual_lower),
            ("residual_upper", self.residual_upper),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{name}_not_finite")
                continue
            if not math.isfinite(float(value)):
                errors.append(f"{name}_not_finite")
        if errors:
            raise ValueError("; ".join(errors))


@dataclass(frozen=True)
class TailDiagnosticStatus:
    """Diagnostic tail status (stagnation detection). ``ledger_only=True``.

    The finite-prefix status is one of three literal values:

    * ``"stagnated"`` — the summable positive schedule mass is collapsing to
      a fixed point under the closed family (``1/r`` style obstruction).
      This is an **adversarial test case**: the ledger surfaces it so the
      operator can confirm the schedule is *not* a general convergence
      certificate, not a proof of model-level convergence.
    * ``"non_stagnated"`` — finite prefix mass is monotone-decreasing or
      otherwise progressing normally.
    * ``"inconclusive"`` — insufficient rounds or no schedule available to
      decide.

    The status NEVER drives a beta write, a pruning decision, or a claim.
    It is a pure diagnostic that prompts a *human or future calibrated
    contract* to escalate. No current code path interprets the status as
    a control signal.

    NOTE: This dataclass is PURE DIAGNOSTIC. It NEVER influences
    ``beta``/``prune``/``claim`` (``ledger_only=True``).
    """

    summable_stagnation_detected: bool
    finite_prefix_status: Literal["stagnated", "non_stagnated", "inconclusive"]
    ledger_only: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        # Semantic validation lives in the validator function. The
        # constructor is intentionally permissive so the validator can
        # be probed independently.
        return None


# ---------------------------------------------------------------------------
# Validators (deterministic, ASCII-only error codes)
# ---------------------------------------------------------------------------


def validate_fresh_noise_cumulative_mass_record(
    record: FreshNoiseCumulativeMassRecord,
) -> tuple[str, ...]:
    """Return a tuple of error codes for ``record``.

    Empty tuple means the record is valid. The validator enforces:

    * ``cycle_id``, ``round_in_cycle`` are non-negative ``int``
    * ``n_cap``, ``n_min``, ``n_max`` are finite ``float``
    * ``finite_prefix_mass`` is finite and non-negative
    * ``capacity_curve`` is a tuple of ``(round, n_cap)`` pairs
    * ``empirical_only`` and ``finite_prefix_only`` are both ``True``
    * ``ledger_only`` is ``True`` (class-level sentinel)
    * ``schedule_family`` is a non-empty ``str``
    """
    errors: list[str] = []

    if not isinstance(record.cycle_id, int) or isinstance(record.cycle_id, bool):
        errors.append(ERR_CYCLE_NOT_INT)
    elif record.cycle_id < 0:
        errors.append(ERR_CYCLE_NEGATIVE)

    if not isinstance(record.round_in_cycle, int) or isinstance(record.round_in_cycle, bool):
        errors.append(ERR_ROUND_NOT_INT)
    elif record.round_in_cycle < 0:
        errors.append(ERR_ROUND_NEGATIVE)

    for name, value in (
        ("n_cap", record.n_cap),
        ("n_min", record.n_min),
        ("n_max", record.n_max),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            errors.append(f"{name}_not_finite")

    if not isinstance(record.finite_prefix_mass, (int, float)) or isinstance(
        record.finite_prefix_mass, bool
    ):
        errors.append(ERR_MASS_NOT_FINITE)
    else:
        f = float(record.finite_prefix_mass)
        if not math.isfinite(f):
            errors.append(ERR_MASS_NOT_FINITE)
        elif f < 0.0:
            errors.append(ERR_MASS_NEGATIVE)

    if not isinstance(record.capacity_curve, tuple):
        errors.append(ERR_CAPACITY_CURVE_NOT_TUPLE)
    else:
        for index, entry in enumerate(record.capacity_curve):
            if not isinstance(entry, tuple) or len(entry) != 2:
                errors.append(f"{ERR_CAPACITY_ENTRY_NOT_PAIR}:{index}")
                continue
            try:
                _coerce_int_nonneg(entry[0], f"capacity_curve[{index}].round")
            except ValueError:
                errors.append(f"capacity_curve:{index}:round_invalid")
            try:
                _coerce_nonneg_float(entry[1], f"capacity_curve[{index}].n_cap")
            except ValueError:
                errors.append(f"capacity_curve:{index}:n_cap_invalid")

    if not record.empirical_only:
        errors.append("empirical_only_must_be_True")
    if not record.finite_prefix_only:
        errors.append("finite_prefix_only_must_be_True")
    if not record.ledger_only:
        errors.append("ledger_only_must_be_True")
    if not isinstance(record.schedule_family, str) or not record.schedule_family:
        errors.append("schedule_family_must_be_non_empty_string")

    return tuple(errors)


def validate_spectral_residual_band_proxy(
    proxy: SpectralResidualBandProxy,
) -> tuple[str, ...]:
    """Return a tuple of error codes for ``proxy``.

    Empty tuple means the proxy is valid. The validator enforces:

    * ``cycle_id`` is a non-negative ``int``
    * ``residual_lower`` and ``residual_upper`` are finite ``float`` with
      ``residual_lower <= residual_upper``
    * ``identification_method`` is ``"linear_gaussian"`` or ``"none"``
    * ``applicability`` is ``"applicable"`` or ``"diagnostic_only"``
    * ``ledger_only`` is ``True``
    """
    errors: list[str] = []

    if not isinstance(proxy.cycle_id, int) or isinstance(proxy.cycle_id, bool):
        errors.append(ERR_CYCLE_NOT_INT)
    elif proxy.cycle_id < 0:
        errors.append(ERR_CYCLE_NEGATIVE)

    for name, value in (("residual_lower", proxy.residual_lower), ("residual_upper", proxy.residual_upper)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{name}_not_finite")
            continue
        if not math.isfinite(float(value)):
            errors.append(f"{name}_not_finite")

    try:
        lower = float(proxy.residual_lower)
        upper = float(proxy.residual_upper)
        if math.isfinite(lower) and math.isfinite(upper) and lower > upper:
            errors.append(ERR_RESIDUAL_ORDER)
    except (TypeError, ValueError):
        # Coercion failures are already captured above.
        pass

    if proxy.identification_method not in ("linear_gaussian", "none"):
        errors.append(f"identification_method_invalid:{proxy.identification_method!r}")
    if proxy.applicability not in ("applicable", "diagnostic_only"):
        errors.append(f"applicability_invalid:{proxy.applicability!r}")
    if not proxy.ledger_only:
        errors.append("ledger_only_must_be_True")

    return tuple(errors)


def validate_tail_diagnostic_status(
    status: TailDiagnosticStatus,
) -> tuple[str, ...]:
    """Return a tuple of error codes for ``status``.

    Empty tuple means the status is valid.
    """
    errors: list[str] = []
    if not isinstance(status.summable_stagnation_detected, bool):
        errors.append(ERR_SUMMABLE_STATUS_INVALID)
    if status.finite_prefix_status not in ("stagnated", "non_stagnated", "inconclusive"):
        errors.append(f"finite_prefix_status_invalid:{status.finite_prefix_status!r}")
    if not status.ledger_only:
        errors.append("ledger_only_must_be_True")
    return tuple(errors)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def empty_diagnostics() -> Mapping[str, Any]:
    """Return a read-only empty diagnostics payload.

    The mapping is intentionally frozen: callers must construct a new mapping
    when they have data to record. Empty diagnostics are a valid state; the
    ledger simply carries no rows for that cycle.
    """
    return MappingProxyType({})


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "ERR_CAPACITY_CURVE_NOT_TUPLE",
    "ERR_CAPACITY_ENTRY_NOT_PAIR",
    "ERR_CYCLE_NEGATIVE",
    "ERR_CYCLE_NOT_INT",
    "ERR_MASS_NEGATIVE",
    "ERR_MASS_NOT_FINITE",
    "ERR_N_CAP_NOT_FINITE",
    "ERR_N_MAX_NOT_FINITE",
    "ERR_N_MIN_NOT_FINITE",
    "ERR_RESIDUAL_LOWER_NOT_FINITE",
    "ERR_RESIDUAL_ORDER",
    "ERR_RESIDUAL_UPPER_NOT_FINITE",
    "ERR_ROUND_NEGATIVE",
    # Error codes
    "ERR_ROUND_NOT_INT",
    "ERR_SUMMABLE_STATUS_INVALID",
    # Dataclasses
    "FreshNoiseCumulativeMassRecord",
    "SpectralResidualBandProxy",
    "TailDiagnosticStatus",
    # Helpers
    "empty_diagnostics",
    # Validators
    "validate_fresh_noise_cumulative_mass_record",
    "validate_spectral_residual_band_proxy",
    "validate_tail_diagnostic_status",
]
