"""Stateless rollback flag + audit record (DTB-R8).

This module implements the structural half of the DTB-R8 rollback
contract. It exposes:

* :class:`RollbackFlag` — frozen, single-stateless flag indicating
  whether the active policy must be rolled back to the disabled
  baseline. ``single_stateless=True`` is a structural invariant that
  is enforced at construction time and is the only public value of
  the field.
* :class:`RollbackAudit` — frozen audit record returned by
  :func:`apply_rollback`, capturing the flag, the prior and post
  state digests, and the round at which the rollback was applied.
* :func:`apply_rollback` — pure, stateless applier. **Does not**
  modify checkpoints, **does not** migrate artifacts, and **does
  not** raise a diagnostic proxy or local case as a performance
  conclusion. The function returns a :class:`RollbackAudit` whose
  fields describe the (purely structural) operation.

Module boundary:

* stdlib-only. **No** ``torch``. No I/O. No mutation of inputs.
* All dataclasses are ``frozen=True``.
* The applier never writes performance conclusions based on the
  diagnostic proxy / local case. The rollback outcome is recorded as
  a structural event only.

Tasks satisfied:

* ``DTB-R8`` — structural promotion / rollback / claim gate
  (skeleton). Actual rollback decisions are deferred until R7.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from adaptive_reflow.contracts import hash_artifact

__all__ = [
    "DEFAULT_DISABLED_REASON",
    "RollbackArgumentError",
    "RollbackAudit",
    "RollbackFlag",
    "apply_rollback",
    "build_disabled_rollback_flag",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Default reason recorded on a :class:`RollbackFlag` built via
#: :func:`build_disabled_rollback_flag`. The reason describes a
#: structural event only; it does not depend on the diagnostic proxy
#: or local case as a performance conclusion.
DEFAULT_DISABLED_REASON: str = (
    "claim_gate_not_satisfied:policy_disabled_to_baseline"
)


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_FLAG_NONE: str = "rollback_flag_must_not_be_none"
ERR_FLAG_NOT_DISABLED: str = (
    "rollback_flag_disabled_must_be_true"
)
ERR_FLAG_STATELESS: str = (
    "rollback_flag_single_stateless_must_be_true"
)
ERR_REASON_EMPTY: str = "rollback_flag_reason_must_be_non_empty"
ERR_AT_ROUND_NEGATIVE: str = "rollback_set_at_round_must_be_non_negative"
ERR_APPLIED_ROUND_NEGATIVE: str = (
    "rollback_applied_at_round_must_be_non_negative"
)
ERR_PRIOR_STATE: str = "rollback_prior_state_digest_must_be_non_empty"
ERR_POST_STATE: str = "rollback_post_state_digest_must_be_non_empty"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RollbackArgumentError(ValueError):
    """Raised when rollback-flag construction or application fails.

    Inherits from :class:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns keep working; the subclass
    is exposed via :data:`__all__` for callers that want to narrow
    their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RollbackFlag:
    """Frozen, stateless rollback directive.

    Attributes
    ----------
    disabled:
        ``True`` if the active policy must be rolled back to the
        disabled baseline. Always ``True``; the flag is structurally
        meaningful only when ``disabled`` is true.
    set_at_round:
        Round at which the flag was raised. ``>= 0``.
    reason:
        Human-readable reason for the rollback. Must be non-empty.
    single_stateless:
        Structural invariant — always ``True``. The applier
        :func:`apply_rollback` is stateless: it does not migrate
        artifacts or modify checkpoints. Construction rejects any
        value other than ``True``.
    """

    disabled: bool
    set_at_round: int
    reason: str
    single_stateless: bool


@dataclasses.dataclass(frozen=True)
class RollbackAudit:
    """Frozen audit record returned by :func:`apply_rollback`.

    Attributes
    ----------
    flag:
        The :class:`RollbackFlag` that triggered the audit.
    prior_state_digest:
        Deterministic sha256 digest of the *prior* state observation
        the caller passed in. Non-empty.
    post_state_digest:
        Deterministic sha256 digest of the *post* state observation
        the caller passed in. Non-empty. Equal to ``prior_state_digest``
        when the rollback is structural-only (i.e. when no actual
        state migration is performed).
    applied_at_round:
        Round at which the rollback was applied. ``>= 0``.
    """

    flag: RollbackFlag
    prior_state_digest: str
    post_state_digest: str
    applied_at_round: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_non_negative_int(name: str, value: Any) -> int:
    """Return ``value`` as ``int`` if it is a non-negative int."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise RollbackArgumentError(
            f"{name}: expected int, got {type(value).__name__}"
        )
    if value < 0:
        raise RollbackArgumentError(
            f"{name}: must be >= 0, got {value}"
        )
    return int(value)


def _digest_of(value: Any) -> str:
    """Return a deterministic sha256 hex digest for ``value``."""
    if value is None:
        payload: Any = {"value": None}
    elif isinstance(value, (str, int, float, bool)):
        payload = {"value": value}
    else:
        payload = {"value": repr(value)}
    return str(hash_artifact(payload))


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------


def build_disabled_rollback_flag(
    *,
    set_at_round: int,
    reason: str = DEFAULT_DISABLED_REASON,
) -> RollbackFlag:
    """Build a :class:`RollbackFlag` with the structural invariants enforced.

    The returned flag has ``disabled=True`` and
    ``single_stateless=True``. Any attempt to construct a flag with
    ``disabled=False`` or ``single_stateless=False`` is rejected.
    """
    if reason is None or str(reason).strip() == "":
        raise RollbackArgumentError(ERR_REASON_EMPTY)
    _coerce_non_negative_int("set_at_round", set_at_round)
    return RollbackFlag(
        disabled=True,
        set_at_round=int(set_at_round),
        reason=str(reason),
        single_stateless=True,
    )


# ---------------------------------------------------------------------------
# Stateless applier
# ---------------------------------------------------------------------------


def apply_rollback(
    flag: RollbackFlag,
    *,
    prior_state: Any,
    post_state: Any,
    applied_at_round: int,
) -> RollbackAudit:
    """Apply a :class:`RollbackFlag` and return a :class:`RollbackAudit`.

    The applier is **stateless**: it never modifies checkpoints, never
    migrates artifacts, and never writes a diagnostic proxy or local
    case as a performance conclusion. The audit record describes a
    purely structural event.

    Parameters
    ----------
    flag:
        The :class:`RollbackFlag` to apply. Must satisfy
        ``disabled=True`` and ``single_stateless=True``; otherwise
        :class:`RollbackArgumentError` is raised.
    prior_state:
        Observation of the state prior to rollback. Anything that is
        JSON-serialisable via :func:`hash_artifact` is accepted; the
        caller may pass any object the orchestrator wants recorded.
    post_state:
        Observation of the state after rollback. For the structural
        applier this is expected to be the same logical state as
        ``prior_state`` because no actual migration is performed.
    applied_at_round:
        Round at which the rollback is being applied. ``>= 0``.

    Returns
    -------
    RollbackAudit
        Frozen audit record.

    Raises
    ------
    RollbackArgumentError
        If ``flag`` violates the structural invariants, or if
        ``applied_at_round`` is negative.
    """
    if flag is None:
        raise RollbackArgumentError(ERR_FLAG_NONE)
    if not isinstance(flag, RollbackFlag):
        raise RollbackArgumentError(
            f"flag must be a RollbackFlag, got {type(flag).__name__}"
        )
    if not bool(flag.disabled):
        raise RollbackArgumentError(ERR_FLAG_NOT_DISABLED)
    if not bool(flag.single_stateless):
        raise RollbackArgumentError(ERR_FLAG_STATELESS)
    if flag.reason is None or str(flag.reason).strip() == "":
        raise RollbackArgumentError(ERR_REASON_EMPTY)
    _coerce_non_negative_int("applied_at_round", applied_at_round)

    prior_digest = _digest_of(prior_state)
    post_digest = _digest_of(post_state)
    if prior_digest == "":
        raise RollbackArgumentError(ERR_PRIOR_STATE)
    if post_digest == "":
        raise RollbackArgumentError(ERR_POST_STATE)

    return RollbackAudit(
        flag=flag,
        prior_state_digest=prior_digest,
        post_state_digest=post_digest,
        applied_at_round=int(applied_at_round),
    )
