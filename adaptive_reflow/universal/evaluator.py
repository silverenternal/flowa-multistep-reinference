"""Universal Evaluator Protocol (DTB-R7 — generic layer).

This module declares the *model-family-agnostic* evaluator contract.
It is **stdlib-only** (no ``torch``, no I/O, no molecule vocabulary)
and replaces the implicit GNINA / QED / ADMET / PoseBusters
assumptions previously baked into ``eval/protocol.py``.

A non-molecular adapter may implement :class:`Evaluator` with any
score+diagnostic surface that fits the two-tuple return contract. The
universal engine consumes only the primary ``score``; secondary
diagnostics are propagated opaquely into the per-bundle ledger.

Public surface
--------------

Protocols
    :class:`Evaluator`

NewType aliases
    :data:`ArtifactHash`

Tasks satisfied:

* ``DTB-R7`` — evaluator contract is universal.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from .envelope import ArtifactHash
from .state import StateBundle

# ---------------------------------------------------------------------------
# NewType aliases
# ---------------------------------------------------------------------------
#
# ``ArtifactHash`` is canonically declared in :mod:`adaptive_reflow.universal.envelope`
# (the envelope module carries the broader envelope NewType set: ``BundleId``,
# ``ComplementBlockerCode``). It is re-exported here so evaluator-only callers
# can import the alias directly from this module without reaching into the
# envelope module. mypy treats both imports as the same NewType because they
# resolve to the same module-level binding.


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Evaluator(Protocol):
    """Generic evaluator contract.

    Implementations MUST be total / deterministic for a given
    ``state_bundle`` input. They MUST NOT mutate their inputs. They
    MUST return ``(score, diagnostics)`` where ``score`` is the primary
    scalar used by the per-channel rule and ``diagnostics`` is an
    opaque mapping of secondary metrics propagated into the ledger.

    The ``calibration_artifact_hash`` property MUST return the
    deterministic hash of the calibration artifact that the
    evaluator was trained against; the engine uses this to fail-closed
    against evaluators whose calibration was not frozen before the
    evaluation began.
    """

    def score(self, state_bundle: StateBundle) -> float: ...

    @property
    def calibration_artifact_hash(self) -> ArtifactHash: ...

    def evaluate(
        self,
        *,
        sample: Mapping[str, Any],
    ) -> tuple[float, Mapping[str, float]]: ...


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_evaluator_artifact_hash(value: Any) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``value`` is a non-empty string artifact hash."""
    errors: list[str] = []
    if value is None:
        return (False, ("evaluator_calibration_artifact_hash_must_not_be_none",))
    if not isinstance(value, str) or not value:
        errors.append("evaluator_calibration_artifact_hash_must_be_non_empty_string")
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ArtifactHash",
    # Protocol
    "Evaluator",
    "validate_evaluator_artifact_hash",
]
