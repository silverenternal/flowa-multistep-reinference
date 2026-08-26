"""Promotion reporting and policy version/hash recording (DTB-R8).

This module implements the structural half of the DTB-R8 promotion
contract. It exposes:

* :class:`PromotionReport` — frozen record describing a single
  promotion event (or, in this skeleton, a *deferred* promotion
  evaluation). The report carries every field named in the brief —
  ``policy_version``, ``policy_hash``, ``gain``, ``invalid_samples``,
  ``cost``, ``failure_modes``, ``calibration_drift``,
  ``disabled_baseline``, ``evaluation_rounds``, the
  :class:`ClaimGateDecision`, ``generated_at_round``, and ``run_id``.
* :class:`PolicyVersionHashRecorder` — append-only recorder for
  ``(run_id, policy_version, policy_hash, at_round)`` tuples. Records
  are immutable once written; ``get_records_for_run`` returns the
  recorded tuples in insertion order.

Module boundary:

* stdlib-only. **No** ``torch``. No I/O. No mutation of inputs.
* :class:`PromotionReport` and the recorded tuples are frozen.
* ``PolicyVersionHashRecorder`` keeps its store as an internal
  ``list[tuple]`` and exposes only the public methods listed below.
* Actual numeric ``gain`` / ``cost`` values are placeholders
  (``DEFERRED_GAIN``, ``DEFERRED_COST``); promotion decisions depend
  on R7 GPU data — see :data:`DEFERRED_R8_REASON`.

Tasks satisfied:

* ``DTB-R8`` — structural promotion / rollback / claim gate
  (skeleton). Actual promotion decisions are deferred until R7.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from adaptive_reflow.contracts import (
    ArtifactHash,
    RunId,
    hash_artifact,
)
from adaptive_reflow.eval.claim_gate import DEFERRED_R8_REASON, ClaimGateDecision

__all__ = [
    "DEFERRED_COST",
    "DEFERRED_GAIN",
    "DEFERRED_R8_REASON",
    "PolicyVersionHashRecorder",
    "PromotionArgumentError",
    "PromotionReport",
    "build_deferred_promotion_report",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Placeholder value for :attr:`PromotionReport.gain` until R7 GPU
#: data lands. Real numbers will be supplied by the runtime boundary
#: once paired-evidence evaluation is performed against actual runs.
DEFERRED_GAIN: float = float("nan")

#: Placeholder value for :attr:`PromotionReport.cost` until R7 GPU
#: data lands.
DEFERRED_COST: float = float("nan")

# Re-export ``DEFERRED_R8_REASON`` from ``claim_gate`` so the canonical
# marker is single-sourced. Local aliases below are kept for backwards
# compatibility with any code that imported the symbol from this module.
_DEFERRED_R8_REASON: str = DEFERRED_R8_REASON


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_REPORT_NONE: str = "promotion_report_must_not_be_none"
ERR_RECORDER_NONE: str = "promotion_recorder_must_not_be_none"
ERR_RUN_ID_EMPTY: str = "promotion_run_id_must_be_non_empty"
ERR_POLICY_ID_EMPTY: str = "promotion_policy_id_must_be_non_empty"
ERR_POLICY_HASH_EMPTY: str = "promotion_policy_hash_must_be_non_empty"
ERR_AT_ROUND_NEGATIVE: str = "promotion_at_round_must_be_non_negative"
ERR_GENERATED_ROUND_NEGATIVE: str = (
    "promotion_generated_at_round_must_be_non_negative"
)
ERR_EVAL_ROUNDS_NEGATIVE: str = (
    "promotion_evaluation_rounds_must_be_non_negative"
)
ERR_INVALID_SAMPLES_NEGATIVE: str = (
    "promotion_invalid_samples_must_be_non_negative"
)
ERR_CALIBRATION_DRIFT_RANGE: str = (
    "promotion_calibration_drift_out_of_unit_interval"
)
ERR_DECISION_VALUE: str = "promotion_claim_gate_decision_unknown_value"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PromotionArgumentError(ValueError):
    """Raised when promotion-report construction fails validation.

    Inherits from :class:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns keep working; the subclass
    is exposed via :data:`__all__` for callers that want to narrow
    their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Promotion report dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PromotionReport:
    """Frozen record describing one promotion (or deferred promotion).

    Attributes
    ----------
    policy_version:
        Versioned identifier of the policy that is being reported on
        (e.g. ``"v0.7.2"``). Free-form string.
    policy_hash:
        Deterministic artifact hash for the policy.
    gain:
        Reported gain over the disabled baseline. **Placeholder**
        (``DEFERRED_GAIN``) until R7 GPU data lands.
    invalid_samples:
        Number of samples that failed validation during the
        evaluation window. ``>= 0``.
    cost:
        Reported cost (in arbitrary units) for the evaluation window.
        **Placeholder** (``DEFERRED_COST``) until R7 GPU data lands.
    failure_modes:
        Tuple of human-readable failure-mode strings observed during
        the evaluation. Sorted, deduplicated.
    calibration_drift:
        Calibration drift relative to the reference artifact. A real
        number in ``[0, 1]`` (or ``None`` when not measured yet).
    disabled_baseline:
        Identifier / hash of the disabled-baseline measurement that
        the report compares against. ``None`` when no baseline is
        recorded yet.
    evaluation_rounds:
        Number of rounds over which the report's statistics were
        gathered. ``>= 0``.
    claim_gate_decision:
        The :class:`ClaimGateDecision` that authorised (or refused
        to authorise) this promotion. Structural evaluation in this
        module always sets this to ``"defer"``.
    generated_at_round:
        Round at which the report was generated. ``>= 0``.
    run_id:
        Identifier of the run that owns this report.
    """

    policy_version: str
    policy_hash: ArtifactHash
    gain: float
    invalid_samples: int
    cost: float
    failure_modes: tuple[str, ...]
    calibration_drift: float | None
    disabled_baseline: str | None
    evaluation_rounds: int
    claim_gate_decision: ClaimGateDecision
    generated_at_round: int
    run_id: RunId


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_non_negative_int(name: str, value: Any) -> int:
    """Return ``value`` as ``int`` if it is a non-negative int."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise PromotionArgumentError(
            f"{name}: expected int, got {type(value).__name__}"
        )
    if value < 0:
        raise PromotionArgumentError(
            f"{name}: must be >= 0, got {value}"
        )
    return int(value)


def _coerce_optional_unit_factor(name: str, value: Any) -> float | None:
    """Return ``value`` as ``float`` if in ``[0, 1]`` or ``None``."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PromotionArgumentError(
            f"{name}: expected float in [0, 1] or None, "
            f"got {type(value).__name__}"
        )
    fv = float(value)
    if fv < 0.0 or fv > 1.0:
        raise PromotionArgumentError(
            f"{ERR_CALIBRATION_DRIFT_RANGE}: {name} must be in [0, 1], "
            f"got {fv!r}"
        )
    return fv


def _coerce_decision(value: Any) -> ClaimGateDecision:
    """Return ``value`` as a valid :class:`ClaimGateDecision`."""
    if value not in ("promote", "rollback", "defer"):
        raise PromotionArgumentError(
            f"{ERR_DECISION_VALUE}: expected one of "
            f"('promote', 'rollback', 'defer'), got {value!r}"
        )
    return value  # type: ignore[return-value]


def _coerce_failure_modes(value: Any) -> tuple[str, ...]:
    """Return ``value`` as a sorted, deduplicated tuple of strings."""
    if value is None:
        return ()
    items = list(value)
    for item in items:
        if not isinstance(item, str):
            raise PromotionArgumentError(
                f"failure_modes entries must be str, got "
                f"{type(item).__name__}"
            )
    return tuple(sorted(set(items)))


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------


def build_deferred_promotion_report(
    *,
    policy_version: str,
    policy_hash: ArtifactHash,
    run_id: RunId,
    generated_at_round: int,
    invalid_samples: int = 0,
    failure_modes: tuple[str, ...] = (),
    evaluation_rounds: int = 0,
    disabled_baseline: str | None = None,
    calibration_drift: float | None = None,
) -> PromotionReport:
    """Build a :class:`PromotionReport` with placeholder gain / cost.

    The returned report always has ``claim_gate_decision == 'defer'``
    because the actual promotion logic is deferred until R7 GPU
    evidence lands; :data:`DEFERRED_R8_REASON` is recorded in the
    report's ``failure_modes`` so downstream consumers see the
    deferral explicitly.
    """
    if policy_version is None or str(policy_version) == "":
        raise PromotionArgumentError(ERR_POLICY_ID_EMPTY)
    if policy_hash is None or str(policy_hash) == "":
        raise PromotionArgumentError(ERR_POLICY_HASH_EMPTY)
    if run_id is None or str(run_id) == "":
        raise PromotionArgumentError(ERR_RUN_ID_EMPTY)
    _coerce_non_negative_int(
        "generated_at_round", generated_at_round
    )
    _coerce_non_negative_int("invalid_samples", invalid_samples)
    _coerce_non_negative_int("evaluation_rounds", evaluation_rounds)
    drift = _coerce_optional_unit_factor(
        "calibration_drift", calibration_drift
    )
    fm = _coerce_failure_modes(failure_modes)
    # Always prepend the deferred-reason marker so it cannot be
    # silently swallowed by callers that pass an empty failure_modes
    # tuple.
    if DEFERRED_R8_REASON not in fm:
        fm = (DEFERRED_R8_REASON,) + fm
    return PromotionReport(
        policy_version=str(policy_version),
        policy_hash=ArtifactHash(str(policy_hash)),
        gain=DEFERRED_GAIN,
        invalid_samples=int(invalid_samples),
        cost=DEFERRED_COST,
        failure_modes=fm,
        calibration_drift=drift,
        disabled_baseline=(
            str(disabled_baseline)
            if disabled_baseline is not None and str(disabled_baseline) != ""
            else None
        ),
        evaluation_rounds=int(evaluation_rounds),
        claim_gate_decision="defer",
        generated_at_round=int(generated_at_round),
        run_id=RunId(str(run_id)),
    )


# ---------------------------------------------------------------------------
# PolicyVersionHashRecorder (DTB-R8, append-only)
# ---------------------------------------------------------------------------


class PolicyVersionHashRecorder:
    """Append-only recorder of ``(run_id, policy_version, policy_hash, at_round)``.

    Records are stored as frozen ``tuple`` entries so they cannot be
    mutated after the fact. The recorder never deletes or rewrites
    entries; the public surface is restricted to:

    * :meth:`write_policy_version_hash`
    * :meth:`get_records_for_run`
    * :meth:`total_records`

    The recorder is intentionally not thread-safe — callers are
    expected to serialise writes through the orchestrator. This
    mirrors the existing :class:`policy_authority.WriterArbitrator`
    pattern (single-writer).
    """

    __slots__ = ("_records",)

    def __init__(self) -> None:
        # Each entry is a tuple
        # ``(run_id, policy_version, policy_hash, at_round)``.
        self._records: list[tuple] = []

    # ---- public API ----------------------------------------------------

    def write_policy_version_hash(
        self,
        run_id: RunId,
        policy_version: str,
        policy_hash: ArtifactHash,
        at_round: int,
    ) -> None:
        """Append a new ``(run_id, policy_version, policy_hash, at_round)`` row.

        Parameters
        ----------
        run_id:
            Identifier of the run that owns this policy version. Must
            be non-empty.
        policy_version:
            Versioned policy identifier (e.g. ``"v0.7.2"``). Must be
            non-empty.
        policy_hash:
            Deterministic hash for this policy version. Must be
            non-empty.
        at_round:
            Round index at which the version was recorded. Must be
            ``>= 0``.

        Raises
        ------
        PromotionArgumentError
            If any argument fails validation.
        """
        if run_id is None or str(run_id) == "":
            raise PromotionArgumentError(ERR_RUN_ID_EMPTY)
        if policy_version is None or str(policy_version) == "":
            raise PromotionArgumentError(ERR_POLICY_ID_EMPTY)
        if policy_hash is None or str(policy_hash) == "":
            raise PromotionArgumentError(ERR_POLICY_HASH_EMPTY)
        _coerce_non_negative_int("at_round", at_round)
        self._records.append(
            (
                RunId(str(run_id)),
                str(policy_version),
                ArtifactHash(str(policy_hash)),
                int(at_round),
            )
        )

    def get_records_for_run(self, run_id: RunId) -> tuple[tuple, ...]:
        """Return all records for ``run_id`` in insertion order.

        Returns an empty tuple when no records exist for the run.
        """
        if run_id is None:
            raise PromotionArgumentError(ERR_RUN_ID_EMPTY)
        target = str(run_id)
        return tuple(
            r for r in self._records if str(r[0]) == target
        )

    @property
    def total_records(self) -> int:
        """Return the total number of recorded rows."""
        return len(self._records)

    def __repr__(self) -> str:
        return (
            f"PolicyVersionHashRecorder(total_records={self.total_records})"
        )


# ---------------------------------------------------------------------------
# Convenience: derive a stable policy-hash from a policy_version
# ---------------------------------------------------------------------------


def derive_policy_hash_from_version(
    run_id: RunId,
    policy_version: str,
    *,
    at_round: int,
) -> ArtifactHash:
    """Return a deterministic artifact hash for ``(run_id, policy_version, at_round)``.

    This helper exists so callers can produce a placeholder
    :class:`ArtifactHash` without invoking the full policy-authority
    pipeline. The hash is derived from the canonical
    ``(run_id, policy_version, at_round)`` tuple.
    """
    if run_id is None or str(run_id) == "":
        raise PromotionArgumentError(ERR_RUN_ID_EMPTY)
    if policy_version is None or str(policy_version) == "":
        raise PromotionArgumentError(ERR_POLICY_ID_EMPTY)
    _coerce_non_negative_int("at_round", at_round)
    payload = {
        "run_id": str(run_id),
        "policy_version": str(policy_version),
        "at_round": int(at_round),
    }
    return hash_artifact(payload)
