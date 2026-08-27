"""Per-round bounded update operator.

Defines the abstract :class:`MergeOperatorProtocol` and three concrete
implementations:

* :class:`BoundedMergeOperator` — the canonical symmetric, capped,
  floor-aware merge that backs ``DTB-R3`` (replaces the legacy
  ``max(prev, dynamic)`` operator with a symmetric bounded merge that
  can both increase and decrease the prior-round fraction while
  respecting a hard ``[floor, cap]`` envelope and per-round
  ``delta_cap_up`` / ``delta_cap_down`` step caps).
* :class:`IdentityOperator` — pass-through (returns ``dynamic``
  verbatim; ignores the cap / floor / delta caps). Useful as a
  reference operator and for back-compat shims where the bounded
  semantics must be disabled.
* :class:`EMAOperator` — exponential moving average (``prev + 0.1 *
  (dynamic - prev)``) with no clamps; useful for smoothed evidence
  accumulation where envelope constraints are enforced elsewhere.

Module boundary:

* stdlib-only. No ``torch``. No I/O. No global state. No mutation of
  inputs.
* Pure functions; identical inputs always yield identical outputs.
* The legacy ``max(previous, dynamic)`` operator is **never** invoked
  inside this module. Any legacy caller must be ported to use
  :class:`BoundedMergeOperator` (or :func:`adaptive_reflow.frame.merge.bounded_merge`).

Public surface:

* :class:`MergeOperatorProtocol`
* :class:`BoundedMergeOperator` + :func:`default_bounded_merge_operator`
* :class:`IdentityOperator`
* :class:`EMAOperator`
* :class:`MergeAuthorityError`
* :data:`MERGE_DEGENERATE_INTERVAL` and the per-error-code constants
  re-exported from the legacy frame module.

Failure modes
-------------

The bounded merge is *fail-closed*: any non-finite value, a
non-numeric type, a negative floor, a cap below the floor, a missing
required argument, or a ``delta_cap`` outside ``[0, 1]`` raises
:exc:`MergeAuthorityError` (subclass of :exc:`ValueError`). The
identity and EMA operators trust their inputs (they do no validation)
— callers that need validation should pair them with a wrapper.
"""

from __future__ import annotations

import math
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Module-level constants (canonical error codes; ASCII only)
# ---------------------------------------------------------------------------


#: Audit code emitted when the per-round delta interval collapses to
#: an empty range (``hi < lo``) so the bounded merge returns the
#: floor. The code carries the envelope values so a downstream audit
#: reader can reproduce the degenerate configuration.
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
#: round's emitted ``bounded_target_fraction``.
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
# Exceptions (fail-closed; surface bad caller input)
# ---------------------------------------------------------------------------


class MergeAuthorityError(ValueError):
    """Raised when :class:`BoundedMergeOperator` rejects its arguments.

    Inherits from :exc:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns continue to work; the
    specific subclass is exposed via :data:`__all__` for callers that
    want to narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Internal coercion helper
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


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MergeOperatorProtocol(Protocol):
    """Abstract per-round bounded update operator.

    Implementations take a previous-round value (``prev``), a dynamic
    evidence-derived value (``dynamic``), and a per-round envelope
    (cap / floor / delta caps). They return a value in ``[floor, cap]``
    — or, for non-clamping operators (identity, EMA), the unconstrained
    update — so the engine can plug in different update philosophies
    without changing the surrounding contract.

    Different operators encode different update philosophies — bounded
    merge (default), EMA (no clamps), identity (pass-through).
    """

    def merge(
        self,
        prev: float,
        dynamic: float,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Return the merged value for one round.

        Parameters
        ----------
        prev:
            Previous-round fraction. Must be finite for clamping
            operators; identity / EMA pass-through do not require
            finiteness but reasonable values are recommended.
        dynamic:
            Dynamic evidence-derived fraction. Must be finite for
            clamping operators.
        cap:
            Hard upper envelope (must be finite, in ``[0, 1]``, and
            ``>= floor``). Ignored by identity / EMA operators.
        floor:
            Hard lower envelope / fresh-noise floor (must be finite,
            in ``[0, 1]``, and ``<= cap``). Ignored by identity / EMA
            operators.
        delta_cap_up:
            Maximum per-round increase (must be finite, in ``[0, 1]``).
            Ignored by identity / EMA operators.
        delta_cap_down:
            Maximum per-round decrease (must be finite, in ``[0, 1]``).
            Ignored by identity / EMA operators.
        audit_codes:
            Optional mutable list that the operator appends diagnostic
            codes to. Clamping operators append
            :data:`MERGE_DEGENERATE_INTERVAL` (with envelope values
            embedded) when the per-round delta interval collapses to
            empty.

        Returns
        -------
        float
            The merged value. Clamping operators guarantee the result
            lies in ``[floor, cap]``; non-clamping operators return
            their unconstrained update.
        """
        ...


# ---------------------------------------------------------------------------
# Default implementation: BoundedMergeOperator
# ---------------------------------------------------------------------------


class BoundedMergeOperator:
    """Canonical symmetric, capped, floor-aware merge (DTB-R3).

    The merge replaces the legacy ``max(prev, dynamic)`` operator with
    a symmetric bounded merge that can both **increase** and
    **decrease** the prior-round fraction, while respecting a hard
    ``[floor, cap]`` envelope and per-round ``delta_cap_up`` /
    ``delta_cap_down`` step caps.

    Concretely, let ``target = clamp(dynamic, floor, cap)``. The
    returned value is

        result = clamp(target, max(floor, prev - delta_cap_down),
                       min(cap, prev + delta_cap_up))

    When the bound interval is empty (e.g. ``floor > cap`` or the two
    delta-caps collapse the interval below the floor) the operator
    returns the floor; this is the documented fail-closed behaviour so
    the merge is total and never raises on legitimate call patterns.
    When ``audit_codes`` is supplied, the merge appends
    :data:`MERGE_DEGENERATE_INTERVAL` (with the envelope values
    embedded for forensic reconstruction) before returning the floor;
    when ``audit_codes`` is ``None`` the collapse is silent for
    back-compat with callers that do not opt into audit emission.

    Parameters
    ----------
    tolerance:
        Reserved tolerance for degenerate-interval detection. The
        current implementation collapses on the strict ``hi < lo``
        comparison, so ``tolerance`` does not currently affect
        behaviour; it is accepted as a constructor argument so future
        near-degenerate handling can be added without changing the
        operator's protocol surface.
    """

    def __init__(self, *, tolerance: float = 1e-9) -> None:
        self._tolerance = float(tolerance)

    @property
    def tolerance(self) -> float:
        """Return the configured degenerate-interval tolerance."""
        return float(self._tolerance)

    def merge(
        self,
        prev: float,
        dynamic: float,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Return the bounded merge of ``prev`` and ``dynamic``."""
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
# Alternative operators (no clamping)
# ---------------------------------------------------------------------------


class IdentityOperator:
    """Pass-through operator that returns ``dynamic`` verbatim.

    The identity operator ignores ``cap`` / ``floor`` / ``delta_cap_up``
    / ``delta_cap_down`` entirely. It is the canonical reference
    operator (and the diagnostic-only fallback that disables the
    envelope semantics while preserving the call site contract).
    """

    def merge(
        self,
        prev: float,
        dynamic: float,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Return ``dynamic`` (cast to ``float``); envelope is ignored."""
        del prev, cap, floor, delta_cap_up, delta_cap_down, audit_codes
        return float(dynamic)


class EMAOperator:
    """Exponential moving average operator (no clamps).

    The smoothed update is

        result = prev + 0.1 * (dynamic - prev)

    — i.e. a 10 % step toward ``dynamic`` from ``prev``. The operator
    ignores ``cap`` / ``floor`` / ``delta_cap_up`` / ``delta_cap_down``
    entirely; callers that need envelope enforcement should wrap it
    with a clamping shim.
    """

    #: Canonical smoothing coefficient. Class-level so tests / callers
    #: can introspect the constant without instantiating.
    ALPHA: float = 0.1

    def __init__(self, *, alpha: float = 0.1) -> None:
        self._alpha = float(alpha)

    @property
    def alpha(self) -> float:
        """Return the smoothing coefficient used by :meth:`merge`."""
        return float(self._alpha)

    def merge(
        self,
        prev: float,
        dynamic: float,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Return the EMA-smoothed update; envelope is ignored."""
        del cap, floor, delta_cap_up, delta_cap_down, audit_codes
        return float(prev) + self._alpha * (float(dynamic) - float(prev))


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_bounded_merge_operator() -> BoundedMergeOperator:
    """Return the canonical :class:`BoundedMergeOperator` singleton-factory.

    The operator is cheap to construct (no state beyond its tolerance),
    so callers may also instantiate :class:`BoundedMergeOperator`
    directly. This factory is the single entry point used by
    :func:`adaptive_reflow.frame.merge.bounded_merge` so the wrapper
    and the canonical operator can never drift.
    """
    return BoundedMergeOperator()


__all__ = [
    "EMAOperator",
    "ERR_PREV_REQUIRED",
    "IdentityOperator",
    "MERGE_DEGENERATE_INTERVAL",
    "MERGE_FLOOR_FALLBACK",
    "MERGE_PREV_ANCHORED_TO_LAST_EMITTED",
    "MergeAuthorityError",
    "MergeOperatorProtocol",
    "BoundedMergeOperator",
    "default_bounded_merge_operator",
]
