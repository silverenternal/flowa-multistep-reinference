"""Operation-composition contract for the adaptive_reflow component.

This module implements the DTB-L2 "operation order" half of the typed
contract. The seven-step default order

    validate -> select -> restart_distribution -> condition_delta ->
    declared_freeze -> native_ODE_solve -> endpoint_observation

is fixed and must be written into every ``RoundTrace`` (see
``CONTRACTS.md`` §6). Any adapter that needs a different order must declare
its own ``operation_order_version`` and provide an order-reversal paired
test plus a bounded commutator-residual diagnostic.

Module boundary:

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* :class:`OperationCompositionContract` is frozen (it is imported from
  :mod:`restart_memory_types`); this module only constructs it.
* :class:`CommutatorResidualDiagnostic` is frozen (also imported); this
  module only fills its fields.

Public surface:

* :data:`DEFAULT_OPERATION_ORDER` — the canonical 7-step tuple.
* :data:`DEFAULT_OPERATION_COMPOSITION_VERSION` — ``"1.0.0"``.
* :data:`DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE` — ``1.0e-8``.
* :func:`build_default_composition_contract` — return the canonical
  contract with deterministic ``contract_hash``.
* :func:`validate_operation_order` — accept any permutation of the seven
  default steps and reject empty / duplicate / unknown / incomplete
  orderings.
* :func:`record_commutator_residual` — build a
  :class:`CommutatorResidualDiagnostic` from paired AB / BA endpoint
  digests, computing a deterministic byte-sum proxy when no explicit
  ``residual_norm`` is supplied.
* :func:`replay_default_order` — pure equality check between a tuple of
  steps and the contract's ``default_order``.

Tasks satisfied:

* ``DTB-L2`` — operation order commutator-safe semantics.
"""

from __future__ import annotations

import hashlib
from typing import Any

from adaptive_reflow.contracts import (
    DEFAULT_OPERATION_ORDER,
    ArtifactHash,
    CommutatorResidualDiagnostic,
    OperationCompositionContract,
    TraceDigest,
    hash_artifact,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


# Re-exported for callers that import this module rather than
# ``restart_memory_types`` directly.
DEFAULT_OPERATION_COMPOSITION_VERSION: str = "1.0.0"
DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE: float = 1.0e-8


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------


ERR_OPERATION_ORDER_EMPTY: str = "operation_order_empty"
ERR_OPERATION_ORDER_DUPLICATE: str = "operation_order_duplicate_steps"
ERR_OPERATION_ORDER_UNKNOWN: str = "operation_order_unknown_step"
ERR_OPERATION_ORDER_INCOMPLETE: str = "operation_order_incomplete"
ERR_VERSION_EMPTY: str = "operation_order_version_must_be_non_empty"
ERR_VERSION_NONE: str = "operation_order_version_must_not_be_none"
ERR_CONTRACT_NONE: str = "contract_must_not_be_none"
ERR_RECORDED_AT_ROUND_NONE: str = "recorded_at_round_must_not_be_none"
ERR_RECORDED_AT_ROUND_NON_INT: str = "recorded_at_round_must_be_int"
ERR_RECORDED_AT_ROUND_NEGATIVE: str = "recorded_at_round_must_be_non_negative"
ERR_RESIDUAL_NORM_NON_NUMERIC: str = "residual_norm_must_be_real_number"
ERR_STEPS_NONE: str = "steps_must_not_be_none"


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _coerce_steps_to_tuple(steps: Any) -> tuple[str, ...]:
    """Coerce ``steps`` to a tuple of ``str`` while preserving order.

    Accepts any iterable of strings (tuple, list, generator). Strings and
    bytes are wrapped in a 1-tuple to keep the function total; callers
    downstream reject that case via :func:`validate_operation_order`.
    """
    if steps is None:
        return ()
    if isinstance(steps, str):
        return (steps,)
    if isinstance(steps, (bytes, bytearray)):
        return (steps.decode("utf-8"),)
    if isinstance(steps, tuple):
        return tuple(str(s) for s in steps)
    if isinstance(steps, list):
        return tuple(str(s) for s in steps)
    # Generators / arbitrary iterables
    return tuple(str(s) for s in steps)


def _digest_byte_sum(digest: Any) -> int:
    """Return ``sum(bytes.fromhex(digest))`` for the supplied digest.

    Digests produced by :func:`hash_artifact` are sha256 hex strings of
    length 64, so ``bytes.fromhex`` always succeeds. For non-hex input we
    fall back to a sha256-derived byte string so the function remains
    deterministic across all NewType-wrapped string inputs.
    """
    text = str(digest)
    try:
        raw = bytes.fromhex(text)
    except ValueError:
        raw = hashlib.sha256(text.encode("utf-8")).digest()
    return int(sum(raw))


def _ensure_non_empty_version(version: Any, field_name: str) -> str:
    """Return ``version`` as ``str``; raise on empty / ``None``."""
    if version is None:
        raise ValueError(f"{field_name} must not be None")
    text = str(version)
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


# ---------------------------------------------------------------------------
# Builders and validators
# ---------------------------------------------------------------------------


def build_default_composition_contract() -> OperationCompositionContract:
    """Return the canonical, frozen :class:`OperationCompositionContract`.

    The returned contract has:

    * ``version`` = :data:`DEFAULT_OPERATION_COMPOSITION_VERSION`
      (currently ``"1.0.0"``).
    * ``operation_order`` and ``default_order`` equal to
      :data:`DEFAULT_OPERATION_ORDER`.
    * ``commutator_residual_tolerance`` =
      :data:`DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE` (``1.0e-8``).
    * ``contract_hash`` = deterministic sha256 of ``(version,
      default_order)``.

    The ``version`` field is fail-closed against empty / ``None`` strings:
    if :data:`DEFAULT_OPERATION_COMPOSITION_VERSION` is ever set to an
    empty value the helper raises :exc:`ValueError`.
    """
    version = _ensure_non_empty_version(
        DEFAULT_OPERATION_COMPOSITION_VERSION, "DEFAULT_OPERATION_COMPOSITION_VERSION"
    )
    default_order = DEFAULT_OPERATION_ORDER
    if not default_order:
        raise ValueError(
            "DEFAULT_OPERATION_ORDER must be non-empty (fail closed: cannot "
            "build a composition contract with no default order)"
        )

    contract_hash = hash_artifact(
        {"version": version, "default_order": list(default_order)}
    )

    return OperationCompositionContract(
        version=version,
        operation_order=default_order,
        default_order=default_order,
        commutator_residual_tolerance=DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE,
        contract_hash=contract_hash,
    )


def validate_operation_order(steps: tuple[str, ...]) -> tuple[str, ...]:
    """Return an empty tuple when ``steps`` is a valid permutation of the
    canonical default order; otherwise a tuple of error codes.

    Validation rules (in this evaluation order — first match wins):

    1. ``steps`` is empty -> ``"operation_order_empty"``.
    2. ``steps`` contains a duplicate value ->
       ``"operation_order_duplicate_steps"``.
    3. ``steps`` contains a value not in
       :data:`DEFAULT_OPERATION_ORDER` ->
       ``"operation_order_unknown_step"``.
    4. ``steps`` is missing one or more canonical entries ->
       ``"operation_order_incomplete"``.

    Any ordering of the seven canonical steps is accepted; non-default
    steps, duplicate steps and an empty ordering are all rejected.
    """
    coerced = _coerce_steps_to_tuple(steps)

    if not coerced:
        return (ERR_OPERATION_ORDER_EMPTY,)

    canonical_set = frozenset(DEFAULT_OPERATION_ORDER)

    seen: set[str] = set()
    for step in coerced:
        if step in seen:
            return (ERR_OPERATION_ORDER_DUPLICATE,)
        seen.add(step)

    unknown = [step for step in coerced if step not in canonical_set]
    if unknown:
        return (ERR_OPERATION_ORDER_UNKNOWN,)

    if seen != canonical_set:
        return (ERR_OPERATION_ORDER_INCOMPLETE,)

    return ()


def record_commutator_residual(
    contract: OperationCompositionContract,
    *,
    ab_endpoint_digest: TraceDigest,
    ba_endpoint_digest: TraceDigest,
    inputs_digest_ab: ArtifactHash,
    inputs_digest_ba: ArtifactHash,
    recorded_at_round: int,
    residual_norm: float | None = None,
) -> CommutatorResidualDiagnostic:
    """Build a :class:`CommutatorResidualDiagnostic` from paired AB / BA
    endpoint digests.

    Parameters
    ----------
    contract:
        The :class:`OperationCompositionContract` that governed the
        paired test. Its ``version`` is propagated as the
        ``operation_order_version`` on the diagnostic.
    ab_endpoint_digest / ba_endpoint_digest:
        Endpoint digests produced by the AB (forward) and BA (reverse)
        orderings of the operation composition.
    inputs_digest_ab / inputs_digest_ba:
        Hashes of the inputs that produced each ordering's endpoint.
    recorded_at_round:
        Round index at which the diagnostic was recorded. Must be a
        non-negative integer.
    residual_norm:
        Explicit residual norm. When ``None``, a deterministic byte-sum
        proxy is computed:

            residual_norm = abs(sum(bytes.fromhex(ab)) - sum(bytes.fromhex(ba)))

        The proxy is documented as a stand-in for the true operator-norm
        residual and is **only** used when the caller has no better
        measurement available. NewType wrappers (``TraceDigest``,
        ``ArtifactHash``) are unwrapped to ``str`` before hex-decoding.

    Raises
    ------
    ValueError
        If ``contract`` is ``None``, ``contract.version`` (the
        ``operation_order_version``) is empty / ``None``, or
        ``recorded_at_round`` is not a non-negative integer.
    """
    if contract is None:
        raise ValueError(ERR_CONTRACT_NONE)
    _ensure_non_empty_version(contract.version, "contract.version (operation_order_version)")

    if recorded_at_round is None:
        raise ValueError(ERR_RECORDED_AT_ROUND_NONE)
    if isinstance(recorded_at_round, bool) or not isinstance(recorded_at_round, int):
        raise ValueError(
            f"{ERR_RECORDED_AT_ROUND_NON_INT}; got {type(recorded_at_round).__name__}"
        )
    if recorded_at_round < 0:
        raise ValueError(
            f"{ERR_RECORDED_AT_ROUND_NEGATIVE}; got {recorded_at_round}"
        )

    if residual_norm is None:
        ab_byte_sum = _digest_byte_sum(ab_endpoint_digest)
        ba_byte_sum = _digest_byte_sum(ba_endpoint_digest)
        residual_norm = float(abs(ab_byte_sum - ba_byte_sum))
    else:
        if isinstance(residual_norm, bool) or not isinstance(residual_norm, (int, float)):
            raise ValueError(
                f"{ERR_RESIDUAL_NORM_NON_NUMERIC}; got {type(residual_norm).__name__}"
            )
        residual_norm = float(residual_norm)

    within_tolerance = bool(residual_norm <= float(contract.commutator_residual_tolerance))

    return CommutatorResidualDiagnostic(
        contract_hash=contract.contract_hash,
        ab_endpoint_digest=ab_endpoint_digest,
        ba_endpoint_digest=ba_endpoint_digest,
        residual_norm=residual_norm,
        within_tolerance=within_tolerance,
        inputs_digest_ab=inputs_digest_ab,
        inputs_digest_ba=inputs_digest_ba,
        operation_order_version=str(contract.version),
        recorded_at_round=int(recorded_at_round),
    )


def replay_default_order(
    contract: OperationCompositionContract,
    steps: tuple[str, ...],
) -> bool:
    """Return ``True`` iff ``steps`` equals ``contract.default_order``.

    Both operands are coerced to tuples of ``str`` and compared element-
    wise. A ``None`` contract, a ``None`` steps value, or a type mismatch
    returns ``False`` (fail-closed equivalence check). The function is
    pure and total: no exception is raised on bad input.
    """
    if contract is None:
        return False
    if steps is None:
        return False
    try:
        coerced_default = tuple(str(s) for s in contract.default_order)
        coerced_steps = _coerce_steps_to_tuple(steps)
    except (TypeError, ValueError):
        return False
    return coerced_steps == coerced_default


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE",
    "DEFAULT_OPERATION_COMPOSITION_VERSION",
    # Constants
    "DEFAULT_OPERATION_ORDER",
    "ERR_CONTRACT_NONE",
    "ERR_OPERATION_ORDER_DUPLICATE",
    # Error codes
    "ERR_OPERATION_ORDER_EMPTY",
    "ERR_OPERATION_ORDER_INCOMPLETE",
    "ERR_OPERATION_ORDER_UNKNOWN",
    "ERR_RECORDED_AT_ROUND_NEGATIVE",
    "ERR_RECORDED_AT_ROUND_NONE",
    "ERR_RECORDED_AT_ROUND_NON_INT",
    "ERR_RESIDUAL_NORM_NON_NUMERIC",
    "ERR_STEPS_NONE",
    "ERR_VERSION_EMPTY",
    "ERR_VERSION_NONE",
    # Builders / validators
    "build_default_composition_contract",
    "record_commutator_residual",
    "replay_default_order",
    "validate_operation_order",
]
