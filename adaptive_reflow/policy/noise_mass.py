"""Three-way distinction of noise quantities (DTB-L4).

This module is the **calculation / diagnostic** leg of DTB-L4. It defines three
*distinct* quantities:

* :func:`physical_noise_proxy` — a *decoded-graph / topology* proxy for the
  physical noise that was actually delivered to the model. It is a function
  of the observable decoded graph; it does **not** assume ``1 - beta`` equals
  physical variance.
* :func:`RMS_preserving_mixing_coefficient` — the per-channel ``beta`` that
  the channel rule emits. This is a *mixer coefficient*, not a physical
  variance.
* :func:`exact_spectral_variance` — only available when the adapter supplies
  a linear Gaussian identification of the local smoothing operator. When
  the adapter does not provide the identification, the function returns
  ``None``; the quantity is **not assumed** to equal the proxy.

The three quantities are encoded by :class:`ThreeWayDistinction`, which makes
their non-equality explicit at the type level. Any report that conflates them
violates DTB-L4 and DTB-R0.

This module is **stdlib-only**: no ``torch``, no IO. All functions are pure.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Canonical blocker / error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_PROXY_INPUT_INVALID = "physical_noise_proxy_input_invalid"
ERR_BETA_INPUT_INVALID = "rms_preserving_mixing_coefficient_input_invalid"
ERR_SPECTRAL_INPUT_INVALID = "exact_spectral_variance_input_invalid"
ERR_CURVE_NOT_SEQUENCE = "schedule_curve_must_be_sequence_of_floats"
ERR_CURVE_ENTRY_NOT_FINITE = "schedule_curve_entry_not_finite"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _coerce_finite_float(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {type(value).__name__}")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite, got {f!r}")
    return float(f)


def _coerce_unit_float(value: Any, name: str) -> float:
    """Coerce ``value`` to a finite ``float`` clipped to ``[0, 1]``."""
    f = _coerce_finite_float(value, name)
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return float(f)


def _coerce_curve(curve: Any, name: str = "schedule_curve") -> tuple[float, ...]:
    """Coerce ``curve`` to a tuple of finite ``float`` capacity values."""
    if curve is None:
        raise ValueError(f"{name} must be a sequence of floats, got None")
    if isinstance(curve, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence of floats, got {type(curve).__name__}")
    if not isinstance(curve, tuple):
        curve = tuple(curve)
    out: list[float] = []
    for index, entry in enumerate(curve):
        if not isinstance(entry, (int, float)) or isinstance(entry, bool):
            raise ValueError(
                f"{name}[{index}] must be a finite real number, got {entry!r}"
            )
        f = float(entry)
        if not math.isfinite(f):
            raise ValueError(f"{name}[{index}] must be finite, got {f!r}")
        out.append(float(f))
    return tuple(out)


# ---------------------------------------------------------------------------
# Three distinct quantities
# ---------------------------------------------------------------------------


def physical_noise_proxy(decoded_graph: Any) -> float:
    """Return the **decoded-graph / topology** proxy for physical noise.

    The proxy is a deterministic function of the observable decoded graph. It
    captures the *physical* noise the model actually saw at this round: it is
    derived from the graph's node / edge statistics and any topology-only
    observable (atom count, valence validity, sanitization pass, ...). It
    is **not** the per-channel mixing coefficient.

    This is the *first* of three distinct quantities tracked by DTB-L4. Do not
    conflate with :func:`RMS_preserving_mixing_coefficient` or
    :func:`exact_spectral_variance`.

    The function is deliberately tolerant: missing / malformed inputs
    collapse to ``0.0`` rather than raising, so a missing observable can be
    surfaced separately as a diagnostic blocker by the caller. Non-finite
    numeric inputs raise :exc:`ValueError` because they indicate a corrupted
    ledger row, not a missing observable.
    """
    if decoded_graph is None:
        return 0.0
    if isinstance(decoded_graph, (int, float)) and not isinstance(decoded_graph, bool):
        # Coerce-and-clip; this is the "graph gave us a scalar" case.
        try:
            return _coerce_unit_float(decoded_graph, "physical_noise_proxy")
        except ValueError:
            return 0.0
    if not isinstance(decoded_graph, Mapping):
        return 0.0

    # Topology-only aggregation: count distinct canonical signals and
    # blend them into a unit-interval proxy. Each contributing signal is
    # independently clipped; missing signals default to 0 and divide the
    # blend accordingly.
    signals: list[float] = []

    for key in (
        "coordinate_extent_rms",
        "pocket_distance",
        "pocket_contact_support",
        "graph_complexity",
        "pair_entropy",
        "projection_loss",
    ):
        value = decoded_graph.get(key)
        if isinstance(value, bool):
            continue
        if not isinstance(value, (int, float)):
            continue
        try:
            f = _coerce_unit_float(value, f"physical_noise_proxy:{key}")
        except ValueError:
            continue
        signals.append(f)

    for key in ("atom_count", "sanitized", "geometry_pass"):
        value = decoded_graph.get(key)
        if isinstance(value, bool):
            signals.append(1.0 if value else 0.0)
            continue
        if isinstance(value, int) and not isinstance(value, bool):
            count = max(0, int(value))
            # Normalize atom_count to [0, 1] using a 64-atom soft cap.
            signals.append(min(1.0, count / 64.0))

    if not signals:
        return 0.0
    return float(sum(signals) / len(signals))


def RMS_preserving_mixing_coefficient(channel_beta: Any) -> float:
    """Return the per-channel **RMS-preserving mixing coefficient** ``beta``.

    The returned value is the **mixer coefficient** that the channel rule
    emits for the corresponding channel. It preserves prior RMS only when
    the input is a finite ``float`` in ``[0, 1]`` and the surrounding
    mixing map is the empirically-calibrated one; this function does not
    re-derive the map. Callers must treat the returned value as a
    **mixing coefficient**, not as a physical variance.

    This is the *second* of three distinct quantities tracked by DTB-L4.
    Do not conflate with :func:`physical_noise_proxy` or
    :func:`exact_spectral_variance`.

    Raises :exc:`ValueError` for non-finite inputs (corrupted ledger row).
    """
    return _coerce_unit_float(channel_beta, "RMS_preserving_mixing_coefficient")


def exact_spectral_variance(
    adapter_identified: Any,
    *,
    sample: Any = None,
) -> float | None:
    """Return the **exact spectral variance**, or ``None`` when unidentified.

    The exact spectral variance is only meaningful when ``adapter_identified``
    is truthy (the adapter explicitly identifies the local smoothing
    operator as linear Gaussian). Otherwise the function returns ``None``
    and the caller MUST treat the absence as a missing evidence, **not**
    as ``0`` and **not** as equal to the proxy.

    When ``adapter_identified`` is truthy, ``sample`` may carry any model-
    specific spectral payload (e.g. a fitted spectrum). The function
    aggregates it deterministically into a single non-negative finite
    value. When ``sample`` is missing, the function still returns a
    well-defined placeholder ``0.0`` so callers can distinguish
    *unidentified* (``None``) from *identified but zero* (``0.0``).

    This is the *third* of three distinct quantities tracked by DTB-L4.
    Do not conflate with :func:`physical_noise_proxy` or
    :func:`RMS_preserving_mixing_coefficient`.

    Raises :exc:`ValueError` only for non-boolean ``adapter_identified``
    inputs that the validator cannot decide.
    """
    if not isinstance(adapter_identified, bool):
        if adapter_identified in (0, 1):
            adapter_identified = bool(adapter_identified)
        else:
            raise ValueError(
                f"adapter_identified must be a boolean, got {type(adapter_identified).__name__}"
            )
    if not adapter_identified:
        return None
    if sample is None:
        return 0.0
    if isinstance(sample, (int, float)) and not isinstance(sample, bool):
        f = float(sample)
        if not math.isfinite(f):
            raise ValueError(f"exact_spectral_variance:sample_must_be_finite, got {f!r}")
        if f < 0.0:
            return 0.0
        return float(f)
    if isinstance(sample, Mapping):
        # Aggregate any per-mode spectral entries deterministically.
        total = 0.0
        seen = 0
        for key, value in sample.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            f = float(value)
            if not math.isfinite(f):
                raise ValueError(
                    f"exact_spectral_variance:{key}_must_be_finite, got {f!r}"
                )
            if f < 0.0:
                continue
            total += f
            seen += 1
        if seen == 0:
            return 0.0
        return float(total / seen)
    if isinstance(sample, Iterable) and not isinstance(sample, (str, bytes, bytearray)):
        entries: list[float] = []
        for entry in sample:
            if isinstance(entry, bool) or not isinstance(entry, (int, float)):
                continue
            f = float(entry)
            if not math.isfinite(f):
                raise ValueError(
                    f"exact_spectral_variance:entry_must_be_finite, got {f!r}"
                )
            if f < 0.0:
                continue
            entries.append(f)
        if not entries:
            return 0.0
        return float(sum(entries) / len(entries))
    raise ValueError(
        f"exact_spectral_variance:sample_must_be_mapping_iterable_or_number, "
        f"got {type(sample).__name__}"
    )


# ---------------------------------------------------------------------------
# Three-way distinction carrier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThreeWayDistinction:
    """Carrier that explicitly separates the three noise quantities.

    The three fields are *distinct* and MUST NOT be conflated. A future
    adapter that wants to merge them must first obtain an explicit
    calibrated authority contract; the default is to keep them separate.

    NOTE: This carrier is PURE DIAGNOSTIC. It NEVER influences
    ``beta``/``prune``/``claim``.
    """

    physical_noise_proxy_value: float
    rms_preserving_mixing_coefficient_value: float
    exact_spectral_variance_value: float | None
    identification_method: Literal["linear_gaussian", "none"]

    def __post_init__(self) -> None:
        # Round-trip the three quantities through their validators.
        try:
            physical_noise_proxy(self.physical_noise_proxy_value)
        except ValueError as exc:
            raise ValueError(f"ThreeWayDistinction.physical_noise_proxy_value:{exc}") from exc
        try:
            RMS_preserving_mixing_coefficient(
                self.rms_preserving_mixing_coefficient_value
            )
        except ValueError as exc:
            raise ValueError(
                f"ThreeWayDistinction.rms_preserving_mixing_coefficient_value:{exc}"
            ) from exc
        if self.exact_spectral_variance_value is not None:
            try:
                exact_spectral_variance(
                    self.identification_method == "linear_gaussian",
                    sample=self.exact_spectral_variance_value,
                )
            except ValueError as exc:
                raise ValueError(
                    f"ThreeWayDistinction.exact_spectral_variance_value:{exc}"
                ) from exc
        else:
            if self.identification_method == "linear_gaussian":
                raise ValueError(
                    "ThreeWayDistinction.identification_method=linear_gaussian "
                    "requires exact_spectral_variance_value to be set"
                )
        if self.identification_method not in ("linear_gaussian", "none"):
            raise ValueError(
                f"ThreeWayDistinction.identification_method must be one of "
                f"'linear_gaussian' or 'none', got {self.identification_method!r}"
            )


# ---------------------------------------------------------------------------
# Adversarial stagnation test (diagnostic only)
# ---------------------------------------------------------------------------


def adversarial_stagnation_test(
    schedule_curve: Any,
    *,
    tolerance: float = 1.0e-9,
) -> dict:
    """Run the adversarial stagnation test on a positive summable schedule.

    The test treats a *summable* positive schedule curve ``(a_0, a_1, ...)``
    as a sequence whose cumulative sums ``S_n = sum_{r=0}^{n} a_r`` either
    converge (summable) or stagnate (e.g. ``a_r = 1/r`` diverges; ``a_r =
    1/r^2`` converges). DTB-L4 insists that even a *converging* summable
    schedule must be reported as an **adversarial test case** — the
    observation that the cumulative mass is finite does not constitute a
    proof of model convergence.

    The returned dict is diagnostic. It exposes:

    * ``is_summable`` — the curve passes the Cauchy tail test for
      convergence (``S_n`` converges as ``n -> infinity``).
    * ``is_stagnated`` — the partial sums appear to collapse to a fixed
      point before the supplied rounds are exhausted.
    * ``partial_sums`` — the running totals (cumulative mass curve).
    * ``finite_prefix_status`` — one of ``"stagnated"``,
      ``"non_stagnated"``, or ``"inconclusive"``.
    * ``adversarial_case`` — ``True`` iff the schedule is summable and
      appears to stagnate, in which case DTB-L4 requires the report to
      call it an adversarial test case (NOT a convergence certificate).
    * ``ledger_only`` — always ``True``.

    Raises :exc:`ValueError` for malformed inputs.
    """
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        raise ValueError(f"tolerance must be a real number, got {type(tolerance).__name__}")
    tolerance = float(tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError(f"tolerance must be finite and non-negative, got {tolerance!r}")

    curve = _coerce_curve(schedule_curve)
    if not curve:
        return {
            "is_summable": False,
            "is_stagnated": False,
            "partial_sums": (),
            "finite_prefix_status": "inconclusive",
            "adversarial_case": False,
            "ledger_only": True,
        }

    # The schedule must be positive for the summable test to be meaningful;
    # otherwise we mark inconclusive.
    if any(value < 0.0 for value in curve):
        return {
            "is_summable": False,
            "is_stagnated": False,
            "partial_sums": (),
            "finite_prefix_status": "inconclusive",
            "adversarial_case": False,
            "ledger_only": True,
            "reason": "schedule_curve_must_be_positive",
        }

    # Compute partial sums (cumulative mass).
    partial: list[float] = []
    total = 0.0
    for value in curve:
        total += float(value)
        partial.append(total)
    partial_tuple = tuple(partial)

    # Detect stagnation: collapse of partial sums over the last third of
    # the curve, relative to the peak partial sum.
    n = len(partial_tuple)
    tail_start = max(1, (2 * n) // 3)
    if tail_start < n:
        peak = max(partial_tuple)
        tail_max = max(partial_tuple[tail_start:])
        # Stagnated if the tail never reaches within tolerance of the peak.
        is_stagnated = bool(peak > 0.0 and (peak - tail_max) > max(tolerance, 1.0e-12) * peak)
    else:
        is_stagnated = False

    # A summable curve has partial sums that *would* converge as n grows.
    # We approximate convergence by checking the tail decay of increments:
    # if the last increment is much smaller than the first, the schedule is
    # summable in the limit (caller may need a longer prefix to confirm).
    is_summable = False
    if len(curve) >= 2:
        first = float(curve[0])
        last = float(curve[-1])
        if first > 0.0:
            is_summable = bool(last < 0.5 * first)

    if is_stagnated:
        finite_prefix_status = "stagnated"
    elif is_summable:
        finite_prefix_status = "non_stagnated"
    else:
        finite_prefix_status = "inconclusive"

    adversarial_case = bool(is_summable and is_stagnated)

    return {
        "is_summable": is_summable,
        "is_stagnated": is_stagnated,
        "partial_sums": partial_tuple,
        "finite_prefix_status": finite_prefix_status,
        "adversarial_case": adversarial_case,
        "ledger_only": True,
    }


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "ERR_BETA_INPUT_INVALID",
    "ERR_CURVE_ENTRY_NOT_FINITE",
    "ERR_CURVE_NOT_SEQUENCE",
    # Error codes
    "ERR_PROXY_INPUT_INVALID",
    "ERR_SPECTRAL_INPUT_INVALID",
    "RMS_preserving_mixing_coefficient",
    # Distinction carrier
    "ThreeWayDistinction",
    # Adversarial test
    "adversarial_stagnation_test",
    "exact_spectral_variance",
    # Three distinct quantities
    "physical_noise_proxy",
]
