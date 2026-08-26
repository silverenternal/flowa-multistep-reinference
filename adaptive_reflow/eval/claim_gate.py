"""Claim gate evaluation for promotion decisions (DTB-R8).

This module implements the structural half of the DTB-R8 promotion /
rollback / claim gate. It exposes:

* :class:`ClaimGateConfig` — frozen configuration describing which
  contracts must pass, which calibration artifact hash must be present,
  how much paired evidence is required, and the
  ``minimum_confidence_interval_coverage`` floor.
* :data:`ClaimGateDecision` — Literal result
  ``("promote", "rollback", "defer")``. The literal values are fixed;
  * only the structural decision rule is implemented here. The actual
  * "promote" / "rollback" decisions require the R7 GPU data which is
  * out of scope for this module — see :data:`DEFERRED_R8_REASON`.
* :class:`ClaimGateEvaluation` — frozen record returned by
  :func:`evaluate_claim_gate` capturing the decision plus the
  per-condition pass/fail tuples, an evidence summary, and the round
  at which the evaluation ran.
* :func:`evaluate_claim_gate` — pure, deterministic, all-or-nothing
  gate evaluator. **Any** missing evidence or unmet condition results
  in a ``"defer"`` decision; the structural promotion logic that
  would turn "all passed" into ``"promote"`` or ``"rollback"`` is
  deferred until R7 GPU data lands.

Module boundary:

* stdlib-only. **No** ``torch``. No I/O. No mutation of inputs.
* All public dataclasses are ``frozen=True``.
* Decision rule is structural: every condition must pass for the
  evaluator to even consider ``"promote"`` / ``"rollback"``. Because
  no R7 GPU data is available, the only structural decision is
  ``"defer"`` — see :data:`DEFERRED_R8_REASON` and the docstring on
  :func:`evaluate_claim_gate`.

Tasks satisfied:

* ``DTB-R8`` — structural promotion / rollback / claim gate
  (skeleton). Actual promotion decisions are deferred until R7.

Notes on evidence structure:

The ``evidence`` argument to :func:`evaluate_claim_gate` is a
``Mapping`` keyed by condition name. Each value is a small record
that includes at least the following keys:

* ``"passed"`` — ``bool``, whether the condition passed.
* ``"summary"`` — optional human-readable string.

The evaluator never assumes any specific structure beyond these two
keys; unknown keys are simply ignored. This keeps the gate strictly
structural — no semantic interpretation of evidence is performed in
this module.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any, Literal

from adaptive_reflow.contracts import ArtifactHash, FactorValue

__all__ = [
    "DEFERRED_R8_REASON",
    "ClaimGateArgumentError",
    "ClaimGateConfig",
    "ClaimGateDecision",
    "ClaimGateEvaluation",
    "evaluate_claim_gate",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Default minimum confidence-interval coverage required when
#: :class:`ClaimGateConfig` is built with explicit field defaults.
DEFAULT_MINIMUM_CONFIDENCE_INTERVAL_COVERAGE: float = 0.0

#: Default number of paired evidence rows required.
DEFAULT_REQUIRED_PAIRED_EVIDENCE_COUNT: int = 0

#: Default evaluation-window length in rounds.
DEFAULT_EVALUATION_WINDOW_ROUNDS: int = 0

#: Default gate-enabled flag. When ``False`` the gate is skipped
#: entirely; :func:`evaluate_claim_gate` returns ``"defer"`` with
#: ``gate_conditions_failed=("gate_disabled",)``.
DEFAULT_GATE_ENABLED: bool = False

#: The set of literal decision values accepted by the gate. These are
#: the only values that can appear in
#: :attr:`ClaimGateEvaluation.decision`.
CLAIM_GATE_DECISION_VALUES: tuple[str, ...] = (
    "promote",
    "rollback",
    "defer",
)

#: Human-readable explanation for why the structural promotion logic
#: beyond ``"defer"`` is not implemented yet. Used in the evidence
#: summary so that downstream consumers see the deferral explicitly.
DEFERRED_R8_REASON: str = (
    "claim gate promotion deferred pending R7 GPU data; structural "
    "evaluation returns 'defer' whenever any required condition is "
    "missing or has not been satisfied"
)


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_CONFIG_NONE: str = "claim_gate_config_must_not_be_none"
ERR_EVIDENCE_NONE: str = "claim_gate_evidence_must_not_be_none"
ERR_ROUND_NEGATIVE: str = "claim_gate_evaluated_at_round_non_negative"
ERR_REQUIRED_PAIRED_NEGATIVE: str = (
    "claim_gate_required_paired_evidence_count_non_negative"
)
ERR_EVAL_WINDOW_NEGATIVE: str = (
    "claim_gate_evaluation_window_rounds_non_negative"
)
ERR_CI_OUT_OF_RANGE: str = (
    "claim_gate_minimum_confidence_interval_coverage_out_of_unit_interval"
)
ERR_CI_NOT_FINITE: str = (
    "claim_gate_minimum_confidence_interval_coverage_not_finite"
)
ERR_ARTIFACT_HASH_TYPE: str = (
    "claim_gate_required_calibration_artifact_hash_wrong_type"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ClaimGateArgumentError(ValueError):
    """Raised when claim-gate construction receives invalid arguments.

    Inherits from :class:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns continue to work; the
    subclass is exposed via :data:`__all__` for callers that want to
    narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ClaimGateConfig:
    """Frozen configuration describing the all-or-nothing claim gate.

    Attributes
    ----------
    required_contracts_passing:
        Tuple of contract identifiers that must all pass. Each
        identifier is matched against a key in the ``evidence``
        mapping supplied to :func:`evaluate_claim_gate`.
    required_calibration_artifact_hash:
        The deterministic artifact hash that calibration evidence
        must carry. When ``None`` the calibration-artifact check is
        skipped. (Real artifact hashes will only be available once R7
        GPU runs land — until then this stays ``None`` and the gate
        defers on the calibration condition.)
    required_paired_evidence_count:
        Minimum number of paired evidence rows required. Must be
        ``>= 0``.
    gate_enabled:
        Master switch. When ``False``, the gate is short-circuited
        to ``"defer"`` with a ``"gate_disabled"`` failure marker.
    evaluation_window_rounds:
        Length of the rolling evaluation window in rounds. Must be
        ``>= 0``.
    minimum_confidence_interval_coverage:
        Minimum confidence-interval coverage required from the
        evidence. Must be finite and in ``[0, 1]``.
    """

    required_contracts_passing: tuple[str, ...]
    required_calibration_artifact_hash: ArtifactHash | None
    required_paired_evidence_count: int
    gate_enabled: bool
    evaluation_window_rounds: int
    minimum_confidence_interval_coverage: FactorValue


# ---------------------------------------------------------------------------
# Decision literal + Evaluation dataclass
# ---------------------------------------------------------------------------


ClaimGateDecision = Literal["promote", "rollback", "defer"]


@dataclasses.dataclass(frozen=True)
class ClaimGateEvaluation:
    """Frozen record of one :func:`evaluate_claim_gate` call.

    Attributes
    ----------
    decision:
        One of ``"promote"``, ``"rollback"``, ``"defer"``. With R7
        GPU data unavailable the only value this module emits is
        ``"defer"``; see :data:`DEFERRED_R8_REASON`.
    gate_conditions_passed:
        Sorted tuple of condition names that passed. Always sorted
        so equality of evaluations is deterministic.
    gate_conditions_failed:
        Sorted tuple of condition names that failed. ``"gate_disabled"``
        is appended when :attr:`ClaimGateConfig.gate_enabled` is
        ``False``. ``"missing_evidence"`` is appended when the
        ``evidence`` mapping is empty / ``None``.
    evidence_summary:
        Plain ``dict`` (string-keyed) summarising what was observed.
        Always contains the keys ``"required_contracts_passing"``,
        ``"required_paired_evidence_count"``,
        ``"evaluation_window_rounds"``,
        ``"minimum_confidence_interval_coverage"``,
        ``"gate_enabled"``, and ``"deferred_reason"``.
    evaluated_at_round:
        Round index at which the gate was evaluated. Must be
        ``>= 0``.
    """

    decision: ClaimGateDecision
    gate_conditions_passed: tuple[str, ...]
    gate_conditions_failed: tuple[str, ...]
    evidence_summary: Mapping[str, Any]
    evaluated_at_round: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_non_negative_int(name: str, value: Any) -> int:
    """Return ``value`` as ``int`` if it is a non-negative int."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ClaimGateArgumentError(
            f"{name}: expected int, got {type(value).__name__}"
        )
    if value < 0:
        raise ClaimGateArgumentError(
            f"{ERR_ROUND_NEGATIVE}: {name} must be >= 0, got {value}"
        )
    return int(value)


def _coerce_unit_factor(name: str, value: Any) -> float:
    """Return ``value`` as ``float`` if finite and in ``[0, 1]``."""
    if isinstance(value, bool):
        # booleans are intentionally rejected: a coverage value is a
        # measurement, not a flag.
        raise ClaimGateArgumentError(
            f"{name}: expected float in [0, 1], got bool"
        )
    if isinstance(value, (int, float)):
        fv = float(value)
    else:
        raise ClaimGateArgumentError(
            f"{name}: expected float in [0, 1], got {type(value).__name__}"
        )
    import math

    if not math.isfinite(fv):
        raise ClaimGateArgumentError(
            f"{ERR_CI_NOT_FINITE}: {name} must be finite, got {fv!r}"
        )
    if fv < 0.0 or fv > 1.0:
        raise ClaimGateArgumentError(
            f"{ERR_CI_OUT_OF_RANGE}: {name} must be in [0, 1], got {fv!r}"
        )
    return fv


def _coerce_artifact_hash(value: Any) -> ArtifactHash | None:
    """Return ``value`` as ``ArtifactHash`` if not ``None``."""
    if value is None:
        return None
    # ArtifactHash is a typing.NewType over str; isinstance() check against
    # the NewType object raises TypeError, so we coerce through ``str``.
    if isinstance(value, str):
        if value == "":
            return None
        return ArtifactHash(value)
    if isinstance(value, ArtifactHash):
        if str(value) == "":
            return None
        return ArtifactHash(str(value))
    raise ClaimGateArgumentError(
        f"{ERR_ARTIFACT_HASH_TYPE}: expected ArtifactHash or None, "
        f"got {type(value).__name__}"
    )


# ---------------------------------------------------------------------------
# Construction helper
# ---------------------------------------------------------------------------


def build_default_claim_gate_config(
    *,
    required_contracts_passing: tuple[str, ...] = (),
    required_calibration_artifact_hash: ArtifactHash | None = None,
    required_paired_evidence_count: int = DEFAULT_REQUIRED_PAIRED_EVIDENCE_COUNT,
    gate_enabled: bool = DEFAULT_GATE_ENABLED,
    evaluation_window_rounds: int = DEFAULT_EVALUATION_WINDOW_ROUNDS,
    minimum_confidence_interval_coverage: float = (
        DEFAULT_MINIMUM_CONFIDENCE_INTERVAL_COVERAGE
    ),
) -> ClaimGateConfig:
    """Build a fully-validated :class:`ClaimGateConfig`.

    All numeric fields are validated as in :class:`ClaimGateConfig`.
    Returns a frozen config that can be reused across many evaluations.
    """
    if required_contracts_passing is None:
        raise ClaimGateArgumentError(
            "required_contracts_passing must not be None"
        )
    contracts_tuple = tuple(str(c) for c in required_contracts_passing)
    # De-duplicate while preserving order so equality is stable.
    seen: set = set()
    deduped: list = []
    for c in contracts_tuple:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    artifact_hash = _coerce_artifact_hash(required_calibration_artifact_hash)
    paired_count = _coerce_non_negative_int(
        "required_paired_evidence_count", required_paired_evidence_count
    )
    window = _coerce_non_negative_int(
        "evaluation_window_rounds", evaluation_window_rounds
    )
    coverage = _coerce_unit_factor(
        "minimum_confidence_interval_coverage",
        minimum_confidence_interval_coverage,
    )
    return ClaimGateConfig(
        required_contracts_passing=tuple(deduped),
        required_calibration_artifact_hash=artifact_hash,
        required_paired_evidence_count=paired_count,
        gate_enabled=bool(gate_enabled),
        evaluation_window_rounds=window,
        minimum_confidence_interval_coverage=FactorValue(float(coverage)),
    )


# ---------------------------------------------------------------------------
# Evaluator (DTB-R8, structural only)
# ---------------------------------------------------------------------------


def evaluate_claim_gate(
    config: ClaimGateConfig,
    evidence: Mapping[str, Any] | None,
    *,
    evaluated_at_round: int,
) -> ClaimGateEvaluation:
    """Evaluate the claim gate and return a :class:`ClaimGateEvaluation`.

    The gate is **all-or-nothing**: every required condition must be
    satisfied for the evaluator to even consider a non-``"defer"``
    decision. With R7 GPU data unavailable, the structural logic
    implemented here always returns ``"defer"`` — see
    :data:`DEFERRED_R8_REASON`.

    Parameters
    ----------
    config:
        The :class:`ClaimGateConfig` describing the gate. Must not be
        ``None``.
    evidence:
        ``Mapping`` keyed by condition name. Each value is itself a
        ``Mapping`` containing at minimum ``"passed"`` (bool) and
        optionally ``"summary"`` (str). ``None`` is treated as an
        empty mapping.
    evaluated_at_round:
        Round index at which the evaluation is being made. Must be
        ``>= 0``.

    Returns
    -------
    ClaimGateEvaluation
        Frozen evaluation record. ``decision`` is always ``"defer"``
        in this module.

    Failure semantics
    -----------------
    * ``config is None`` → :class:`ClaimGateArgumentError`.
    * ``evidence is None`` → :class:`ClaimGateArgumentError` is **not**
      raised; the evaluator treats this as "missing evidence" and
      emits a ``"missing_evidence"`` failure marker with
      ``"defer"``.
    * ``evaluated_at_round < 0`` →
      :class:`ClaimGateArgumentError`.
    * :attr:`ClaimGateConfig.gate_enabled` is ``False`` →
      ``"defer"`` with ``"gate_disabled"`` in
      ``gate_conditions_failed``.
    """
    if config is None:
        raise ClaimGateArgumentError(ERR_CONFIG_NONE)
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, Mapping):
        raise ClaimGateArgumentError(
            f"{ERR_EVIDENCE_NONE}: evidence must be a Mapping, "
            f"got {type(evidence).__name__}"
        )
    _coerce_non_negative_int("evaluated_at_round", evaluated_at_round)

    passed: list = []
    failed: list = []

    # 0. Missing-evidence marker: when the evidence mapping is empty
    #    the structural evaluator cannot satisfy any condition; we
    #    surface an explicit marker so downstream consumers can
    #    distinguish "no evidence was supplied" from "evidence was
    #    supplied and a specific condition failed".
    evidence_is_empty = len(evidence) == 0

    # 1. Master switch: when the gate is disabled, defer unconditionally.
    if not bool(config.gate_enabled):
        failed.append("gate_disabled")
    else:
        if evidence_is_empty:
            failed.append("missing_evidence")
        # 2. Required contracts: each contract id must be present in
        #    the evidence mapping AND must have passed=True.
        for contract_id in config.required_contracts_passing:
            cond_evidence = evidence.get(contract_id)
            if not isinstance(cond_evidence, Mapping):
                failed.append(f"contract_missing:{contract_id}")
                continue
            cond_passed = cond_evidence.get("passed", False)
            if isinstance(cond_passed, bool) and cond_passed:
                passed.append(f"contract:{contract_id}")
            else:
                failed.append(f"contract_failed:{contract_id}")

        # 3. Calibration artifact hash: if required, evidence must
        #    carry the matching hash. Without R7 data this stays
        #    deferred.
        if config.required_calibration_artifact_hash is not None:
            expected_hash = str(config.required_calibration_artifact_hash)
            calib_evidence = evidence.get("calibration_artifact")
            observed_hash = (
                str(calib_evidence.get("hash", ""))
                if isinstance(calib_evidence, Mapping)
                else ""
            )
            if observed_hash == "":
                failed.append("calibration_artifact:missing")
            elif observed_hash != expected_hash:
                failed.append("calibration_artifact:mismatch")
            else:
                passed.append("calibration_artifact")

        # 4. Required paired-evidence count.
        paired_evidence = evidence.get("paired_evidence_count")
        observed_paired = (
            int(paired_evidence)
            if isinstance(paired_evidence, int) and not isinstance(paired_evidence, bool)
            else 0
        )
        if observed_paired >= int(config.required_paired_evidence_count):
            passed.append("paired_evidence_count")
        else:
            failed.append("paired_evidence_count:insufficient")

        # 5. Minimum confidence-interval coverage.
        ci_evidence = evidence.get("confidence_interval_coverage")
        observed_ci = (
            float(ci_evidence)
            if isinstance(ci_evidence, (int, float))
            and not isinstance(ci_evidence, bool)
            else 0.0
        )
        if observed_ci >= float(config.minimum_confidence_interval_coverage):
            passed.append("confidence_interval_coverage")
        else:
            failed.append("confidence_interval_coverage:insufficient")

        # 6. Evaluation-window requirement: structurally the gate
        #    needs at least one round of evidence.
        window_evidence = evidence.get("evaluation_window_rounds")
        observed_window = (
            int(window_evidence)
            if isinstance(window_evidence, int) and not isinstance(window_evidence, bool)
            else 0
        )
        if observed_window >= int(config.evaluation_window_rounds):
            passed.append("evaluation_window_rounds")
        else:
            failed.append("evaluation_window_rounds:insufficient")

    summary: dict = {
        "required_contracts_passing": list(config.required_contracts_passing),
        "required_paired_evidence_count": int(
            config.required_paired_evidence_count
        ),
        "evaluation_window_rounds": int(config.evaluation_window_rounds),
        "minimum_confidence_interval_coverage": float(
            config.minimum_confidence_interval_coverage
        ),
        "gate_enabled": bool(config.gate_enabled),
        "required_calibration_artifact_hash": (
            str(config.required_calibration_artifact_hash)
            if config.required_calibration_artifact_hash is not None
            else None
        ),
        "deferred_reason": DEFERRED_R8_REASON,
    }

    # Structural decision: with R7 data unavailable the only
    # structural value is "defer". We never emit "promote" or
    # "rollback" from this module.
    decision: ClaimGateDecision = "defer"

    return ClaimGateEvaluation(
        decision=decision,
        gate_conditions_passed=tuple(sorted(passed)),
        gate_conditions_failed=tuple(sorted(failed)),
        evidence_summary=dict(summary),
        evaluated_at_round=int(evaluated_at_round),
    )
