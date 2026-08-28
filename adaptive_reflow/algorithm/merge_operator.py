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

The merge operators are **clip-and-audit** (closes P0-3): out-of-range
or non-finite inputs are coerced into ``[0, 1]`` (or the appropriate
envelope sub-range) and the operator appends a canonical audit code
to the caller's ``audit_codes`` list when one is supplied. The bounded
merge appends :data:`MERGE_DEGENERATE_INTERVAL` when the envelope
collapses to an empty interval; the identity and EMA operators append
:data:`MERGE_NONFINITE_PREV_CLIPPED` /
:data:`MERGE_NONFINITE_DYNAMIC_CLIPPED` when ``prev`` / ``dynamic``
are non-finite.

Non-numeric types and ``None`` values still raise
:exc:`MergeAuthorityError` (subclass of :exc:`ValueError`); the
numeric coercion boundary is the only point where an exception may
propagate. The :data:`MergeAuthorityError` codes
``merge_cap_above_one`` / ``merge_floor_above_one`` /
``merge_cap_below_floor`` are still emitted as audit codes when
clamping engages — they are not raised as exceptions any more.
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

#: Audit code emitted when a non-finite ``prev`` was clipped into the
#: unit interval ``[0, 1]`` by a non-clamping operator (P0-3).
MERGE_NONFINITE_PREV_CLIPPED: str = "merge_nonfinite_prev_clipped"

#: Audit code emitted when a non-finite ``dynamic`` was clipped into
#: the unit interval ``[0, 1]`` by a non-clamping operator (P0-3).
MERGE_NONFINITE_DYNAMIC_CLIPPED: str = "merge_nonfinite_dynamic_clipped"

#: Audit code emitted when ``cap`` is clipped from a value outside
#: ``[0, 1]`` into the unit interval by :class:`BoundedMergeOperator`
#: (P0-3 — the operator clips instead of raising).
MERGE_CAP_OUT_OF_RANGE: str = "merge_cap_out_of_range"

#: Audit code emitted when ``floor`` is clipped from a value outside
#: ``[0, 1]`` into the unit interval by :class:`BoundedMergeOperator`
#: (P0-3 — the operator clips instead of raising).
MERGE_FLOOR_OUT_OF_RANGE: str = "merge_floor_out_of_range"

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


def _coerce_unit_real(x: Any, *, name: str) -> float:
    """Return ``float(x)`` with non-numeric / ``None`` inputs raising.

    Booleans are coerced to 0/1; non-finite numeric values are kept
    as the ``float`` representation so the caller's clip-and-audit
    logic can observe them. The helper never raises on finiteness —
    the call site is responsible for the audit emission.
    """
    if x is None:
        raise MergeAuthorityError(f"{name}: required (got None)")
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise MergeAuthorityError(
            f"{name}: expected a real number, got {type(x).__name__}"
        )
    return float(x)


def _coerce_unit_real_clip(
    x: Any,
    *,
    name: str,
    audit_codes: list[str] | None,
    code: str,
) -> tuple[float, bool]:
    """Return ``(float, was_clipped)`` with non-finite / out-of-range
    inputs clipped into ``[0, 1]`` and the audit code appended.

    Used by the operators to satisfy the P0-3 contract
    ("return a finite ``float`` in ``[0, 1]``; do NOT raise on
    non-finite callers"). Numeric inputs that already lie in ``[0, 1]``
    pass through untouched. Out-of-range / non-finite numerics are
    clipped:

    * ``NaN`` -> ``0.0`` (the safe default for an undefined value).
    * ``+inf`` or value ``> 1`` -> ``1.0``.
    * ``-inf`` or value ``< 0`` -> ``0.0``.

    Non-numeric / ``None`` inputs still raise via the inner coercion.
    """
    fx = _coerce_unit_real(x, name=name)
    if math.isfinite(fx) and 0.0 <= fx <= 1.0:
        return fx, False
    if math.isnan(fx):
        clipped = 0.0
    elif fx > 0.0:
        # ``+inf`` and positive out-of-range values saturate to ``1.0``.
        clipped = 1.0
    else:
        # ``-inf`` and negative values saturate to ``0.0``.
        clipped = 0.0
    if audit_codes is not None:
        audit_codes.append(f"{code}:{name}={fx!r}")
    return clipped, True


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MergeOperatorProtocol(Protocol):
    """Abstract per-round bounded update operator.

    Implementations take a previous-round value (``prev``), a dynamic
    evidence-derived value (``dynamic``), and a per-round envelope
    (cap / floor / delta caps) and return a value in ``[floor, cap]``
    — or, for non-clamping operators (identity, EMA), the unconstrained
    update — so the engine can plug in different update philosophies
    without changing the surrounding contract.

    Different operators encode different update philosophies — bounded
    merge (default), EMA (no clamps), identity (pass-through).

    CONTRACT (closes P0-3): all implementations MUST return a finite
    ``float`` in the closed unit interval ``[0, 1]``. Implementations
    MUST NOT raise on legitimate caller input such as ``cap > 1``,
    ``cap < floor``, or non-finite ``dynamic`` / ``prev``; instead,
    they clip / coerce the input to ``[0, 1]`` and (when ``audit_codes``
    is supplied) append the canonical diagnostic code
    (:data:`MERGE_DEGENERATE_INTERVAL`,
    :data:`MERGE_FLOOR_FALLBACK`, or a ValueError-style audit line).
    Clamping operators that normally validate their envelope MUST
    still survive caller inputs that pass ``cap > 1`` or ``cap <
    floor`` by clipping ``cap`` to ``min(1.0, cap)`` and ``floor`` to
    ``max(0.0, min(cap, floor))`` before computing the result; the
    audit trail records the degenerate configuration so downstream
    audit readers can replay it.
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
            Previous-round fraction. Operators MUST coerce non-finite
            values to a finite ``[0, 1]`` clip rather than raising
            (closes P0-3).
        dynamic:
            Dynamic evidence-derived fraction. Operators MUST coerce
            non-finite values to a finite ``[0, 1]`` clip rather than
            raising (closes P0-3).
        cap:
            Hard upper envelope. Operators MUST accept any finite
            value and clip to ``[0, 1]`` rather than raising on
            ``cap > 1`` (closes P0-3). The clipping operator appends
            :data:`MERGE_DEGENERATE_INTERVAL` (with envelope values
            embedded) when the per-round delta interval collapses to
            empty.
        floor:
            Hard lower envelope / fresh-noise floor. Operators MUST
            accept any finite value and clip to ``[0, 1]`` rather than
            raising on ``floor < 0`` or ``floor > cap`` (closes P0-3).
        delta_cap_up:
            Maximum per-round increase. Operators MUST accept any
            finite value and clip to ``[0, 1]``.
        delta_cap_down:
            Maximum per-round decrease. Operators MUST accept any
            finite value and clip to ``[0, 1]``.
        audit_codes:
            Optional mutable list that the operator appends diagnostic
            codes to. Clamping operators append
            :data:`MERGE_DEGENERATE_INTERVAL` (with envelope values
            embedded) when the per-round delta interval collapses to
            empty; operators append a finiteness audit line when they
            clip non-finite ``prev`` / ``dynamic`` to ``[0, 1]``.

        Returns
        -------
        float
            The merged value. Per the contract above the result MUST
            be a finite ``float`` in ``[0, 1]``. Clamping operators
            further guarantee the result lies in the (clipped) ``[floor,
            cap]`` envelope; non-clamping operators still clip their
            unconstrained update into ``[0, 1]``.
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

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": "bounded", "tolerance": float(self._tolerance)}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> BoundedMergeOperator:
        """Build a :class:`BoundedMergeOperator` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return BoundedMergeOperator(tolerance=float(config.get("tolerance", 1e-9)))

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
        """Return the bounded merge of ``prev`` and ``dynamic`` (P0-3).

        The operator uses a **clip-and-audit** policy (closes P0-3): any
        envelope / ``prev`` / ``dynamic`` value that would otherwise
        have triggered a :exc:`MergeAuthorityError` is clipped into the
        documented envelope (``[0, 1]`` for cap / floor / delta caps;
        ``[0, 1]`` for non-finite ``prev`` / ``dynamic``) and the
        canonical audit code is appended to ``audit_codes`` when one
        is supplied. The numeric-coercion boundary is the only point
        where an exception may propagate (a non-numeric type or
        ``None`` still raises :exc:`MergeAuthorityError`).

        The result is guaranteed to be a finite ``float`` in ``[0, 1]``
        regardless of caller input.
        """
        # First, the coercion boundary: a non-numeric type or ``None``
        # still raises. Finite values are clipped into ``[0, 1]`` and a
        # diagnostic audit code is appended when the input was outside
        # the documented envelope (closes P0-3).
        prev_f, _prev_audit = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _dynamic_audit = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )

        # Cap and floor use the same clip-and-audit surface as
        # ``prev`` / ``dynamic`` (closes P0-3): non-finite or
        # out-of-range numeric inputs are clipped into ``[0, 1]`` and
        # the canonical audit code is appended.
        cap_f, _ = _coerce_unit_real_clip(
            cap, name="cap", audit_codes=audit_codes,
            code=MERGE_CAP_OUT_OF_RANGE,
        )
        floor_f, _ = _coerce_unit_real_clip(
            floor, name="floor", audit_codes=audit_codes,
            code=MERGE_FLOOR_OUT_OF_RANGE,
        )

        # Delta caps are clipped into ``[0, 1]`` silently (no audit
        # emission — the legacy bounded-merge math stays
        # byte-identical for ``delta_cap`` adjustments).
        up_f = max(0.0, min(1.0, _coerce_unit_real(delta_cap_up, name="delta_cap_up")))
        down_f = max(
            0.0, min(1.0, _coerce_unit_real(delta_cap_down, name="delta_cap_down"))
        )

        # If ``cap < floor`` after clipping (the only path that can
        # still reach this state, since both are in ``[0, 1]`` post-clip),
        # collapse the envelope to ``(cap=floor_cap, floor=cap)`` so the
        # bounded merge below stays total. The audit code
        # ``MERGE_DEGENERATE_INTERVAL`` is appended so a downstream
        # audit reader can see the clip.
        if cap_f < floor_f:
            new_cap = floor_f
            new_floor = cap_f
            if audit_codes is not None:
                audit_codes.append(
                    f"{_ERR_CAP_BELOW_FLOOR}:cap={cap_f:.6f}:floor={floor_f:.6f}"
                )
            cap_f = new_cap
            floor_f = new_floor

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
            # ``_prev_audit`` / ``_dynamic_audit`` are the audit
            # side-effects from the clip step above; the operator
            # returns the (clipped) floor. Silence the unused-but-set
            # lint explicitly.
            del _prev_audit, _dynamic_audit
            return float(floor_f)

        # Silence the unused-but-set lint explicitly.
        del _prev_audit, _dynamic_audit
        return float(max(lo, min(hi, target)))


# ---------------------------------------------------------------------------
# Alternative operators (no clamping)
# ---------------------------------------------------------------------------


class IdentityOperator:
    """Pass-through operator that returns ``dynamic`` verbatim (P0-3).

    No configuration knobs — ``to_config`` returns
    ``{"family": "identity"}`` and ``from_config`` returns a fresh
    instance for the same dict.

    The identity operator ignores ``cap`` / ``floor`` / ``delta_cap_up``
    / ``delta_cap_down`` entirely. It is the canonical reference
    operator (and the diagnostic-only fallback that disables the
    envelope semantics while preserving the call site contract).

    Per the :data:`MergeOperatorProtocol` contract (P0-3), the
    operator clips non-finite / out-of-range ``dynamic`` into the
    closed unit interval ``[0, 1]`` rather than raising and appends
    :data:`MERGE_NONFINITE_DYNAMIC_CLIPPED` /
    :data:`MERGE_NONFINITE_PREV_CLIPPED` to ``audit_codes`` when one
    is supplied. ``prev`` is not consulted by ``merge`` but is still
    finiteness-checked so the operator surface stays total and the
    documented contract ('all implementations MUST return a finite '
    '``float`` in ``[0, 1]``') can be fulfilled under hostile inputs.
    """

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": "identity"}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> IdentityOperator:
        """Build an :class:`IdentityOperator` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return IdentityOperator()

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
        """Return ``dynamic`` cast to ``float`` and clipped into ``[0, 1]``.

        Non-finite or out-of-range ``dynamic`` is clipped into the
        unit interval (``NaN`` and negative values -> ``0.0``;
        ``inf`` and values ``> 1`` -> ``1.0``) and the canonical
        audit code is appended to ``audit_codes`` when one is
        supplied (closes P0-3).
        """
        del cap, floor, delta_cap_up, delta_cap_down
        prev_f, _prev_audit = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _dynamic_audit = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )
        # ``_prev_audit`` / ``_dynamic_audit`` are the audit side-effects;
        # the operator returns the (clipped) ``dynamic``. Silence the
        # unused-but-set lint explicitly.
        del _prev_audit, _dynamic_audit
        return float(dynamic_f)


class EMAOperator:
    """Exponential moving average operator (no clamps) (P0-3).

    The smoothed update is

        result = prev + alpha * (dynamic - prev)

    — i.e. a ``alpha`` step toward ``dynamic`` from ``prev``. The
    operator ignores ``cap`` / ``floor`` / ``delta_cap_up`` /
    ``delta_cap_down`` entirely; callers that need envelope
    enforcement should wrap it with a clamping shim.

    Per the :data:`MergeOperatorProtocol` contract (P0-3), the
    operator clips non-finite / out-of-range ``prev`` and ``dynamic``
    into the closed unit interval ``[0, 1]`` rather than raising and
    appends the canonical audit code to ``audit_codes`` when one is
    supplied. The EMA step is computed on the clipped values and the
    final result is again clipped into ``[0, 1]`` so the documented
    ("MUST return a finite ``float`` in ``[0, 1]``") contract holds.
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

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": "ema", "alpha": float(self._alpha)}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> EMAOperator:
        """Build an :class:`EMAOperator` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return EMAOperator(alpha=float(config.get("alpha", EMAOperator.ALPHA)))

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
        """Return the EMA-smoothed update, clipped into ``[0, 1]``.

        Non-finite or out-of-range ``prev`` / ``dynamic`` is clipped
        into the unit interval and the canonical audit code is
        appended to ``audit_codes`` when one is supplied (closes
        P0-3). Envelope arguments (``cap``, ``floor``, etc.) are
        ignored by the EMA step but the operator never raises on
        their values either.
        """
        del cap, floor, delta_cap_up, delta_cap_down
        prev_f, _prev_audit = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _dynamic_audit = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )
        # Silence the unused-but-set lint explicitly.
        del _prev_audit, _dynamic_audit
        raw = prev_f + self._alpha * (dynamic_f - prev_f)
        # Final clip into ``[0, 1]`` — defensive against alpha outside
        # ``[0, 1]``. Operators usually configure ``alpha`` in
        # ``(0, 1)`` so the raw EMA is already bounded, but we clip
        # defensively to honour the P0-3 contract.
        if not math.isfinite(raw):
            return 0.0
        if raw < 0.0:
            return 0.0
        if raw > 1.0:
            return 1.0
        return float(raw)


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
    "MERGE_CAP_OUT_OF_RANGE",
    "MERGE_DEGENERATE_INTERVAL",
    "MERGE_FLOOR_FALLBACK",
    "MERGE_FLOOR_OUT_OF_RANGE",
    "MERGE_NONFINITE_DYNAMIC_CLIPPED",
    "MERGE_NONFINITE_PREV_CLIPPED",
    "MERGE_PREV_ANCHORED_TO_LAST_EMITTED",
    "MergeAuthorityError",
    "MergeOperatorProtocol",
    "BoundedMergeOperator",
    "default_bounded_merge_operator",
]
