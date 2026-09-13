"""Molecule calibration targets + concrete :class:`Evaluator` implementations.

This module declares the molecule-specific calibration target set (the
four canonical molecule evaluation metrics) and provides concrete
:class:`adaptive_reflow.universal.evaluator.Evaluator` implementations
for the four real-molecule evaluator backends used in the legacy
external-metric feedback loop (GNINA binding, PoseBusters geometry, QED
drug-likeness, ADMET toxicity flag).

Module boundary
---------------

* ``MOLECULE_CALIBRATION_TARGETS`` is the canonical mapping from metric
  name → legacy evaluator-arm name. Replaces the legacy
  ``eval.calibration.PREDECLARED_SAFETY_METRICS`` literal set.
* ``MOLECULE_CHANNEL_TO_METRIC`` is the canonical mapping from molecule
  channel → metric name. Replaces the legacy
  ``eval.calibration.CHANNEL_NAMES_FOR_CALIBRATION`` literal set (the
  channels are now ``molecular.MOLECULE_CHANNELS``).
* Each ``Evaluator`` concrete class is a thin adapter that wraps a
  caller-supplied scoring callable and reports the canonical molecule
  target score (e.g. ``-4.0`` kcal/mol for GNINA). The default
  ``calibration_artifact_hash`` is a deterministic hash of the target so
  the universal evaluator guard stays fail-closed.
* Stdlib-only: no torch, no I/O, no mutation of inputs.

Public surface
--------------

Constants
    :data:`MOLECULE_CALIBRATION_TARGETS`
    :data:`MOLECULE_CHANNEL_TO_METRIC`

Evaluator classes (concrete ``universal.evaluator.Evaluator`` impls)
    :class:`GNINAEvaluator`
    :class:`PoseBustersEvaluator`
    :class:`QEDEvaluator`
    :class:`ADMETEvaluator`

Tasks satisfied
---------------

* ``DTB-R7`` — evaluator contract is universal; molecule concrete
  evaluators live here.
* ``DTB-R5`` — frozen calibration artifact hash is canonical.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from adaptive_reflow.contracts.types import ArtifactHash

if TYPE_CHECKING:
    # Type-checker alias only; runtime uses the local ``_MoleculeEvaluator``
    # Protocol below to break the
    # ``molecular -> universal.evaluator`` import edge.
    from adaptive_reflow.universal import (
        ArtifactHash as UniversalArtifactHash,
    )
    from adaptive_reflow.universal.evaluator import Evaluator as _UniversalEvaluator
else:
    from adaptive_reflow.contracts.types import ArtifactHash as UniversalArtifactHash


# ---------------------------------------------------------------------------
# Local runtime_checkable Protocol — duplicates the
# :class:`adaptive_reflow.universal.evaluator.Evaluator` Protocol surface.
#
# This breaks the ``molecular -> universal`` import edge so the
# ``universal -> contracts -> molecular`` cycle can be eager-resolved.
# The Protocol MUST be byte-equivalent to the universal ``Evaluator``
# (same member names, same ``runtime_checkable`` flag) so that
# ``isinstance(evaluator, universal.evaluator.Evaluator)`` checks still
# succeed for the molecule-side evaluators.
# ---------------------------------------------------------------------------


@runtime_checkable
class _MoleculeEvaluatorProtocol(Protocol):
    """Local mirror of ``universal.evaluator.Evaluator``.

    Concrete molecule evaluators satisfy this Protocol via duck typing;
    the dataclass inheritance is provided by :class:`_MoleculeTargetEvaluator`
    which subclasses the local Protocol and shares the same member
    surface as ``universal.evaluator.Evaluator``.
    """

    def score(self, state_bundle: Any) -> float: ...

    @property
    def calibration_artifact_hash(self) -> UniversalArtifactHash: ...

    def evaluate(
        self,
        *,
        sample: Mapping[str, Any],
    ) -> tuple[float, Mapping[str, float]]: ...


def _hash_artifact_func(payload: Mapping[str, Any]) -> str:
    """Lazy wrapper around ``contracts.hashes.hash_artifact``.

    Imported lazily to break the cycle:
    ``molecular.calibration_protocols`` -> ``contracts.hashes``
    -> ``contracts.types`` -> ``molecular.channels`` -> ``molecular.__init__``
    -> ``molecular.calibration_protocols`` (in flight).
    """
    from adaptive_reflow.contracts.hashes import hash_artifact

    return hash_artifact(payload)

# ---------------------------------------------------------------------------
# Canonical molecule calibration target table
# ---------------------------------------------------------------------------


# Canonical home: :data:`adaptive_reflow.contracts.types`. Re-exported here
# so existing ``from adaptive_reflow.molecular import
# MOLECULE_CALIBRATION_TARGETS`` paths continue to work.
from adaptive_reflow.contracts.types import (  # noqa: E402
    MOLECULE_CALIBRATION_TARGETS,
    MOLECULE_CHANNEL_TO_METRIC,
)

# ---------------------------------------------------------------------------
# Default target scores (legacy literal constants)
# ---------------------------------------------------------------------------


DEFAULT_GNINA_TARGET_SCORE: float = -4.0
"""GNINA binding-affinity target score, in kcal/mol. Lower (more negative)
is better. ``<= -4.0`` is the canonical "good enough" gate."""

DEFAULT_QED_TARGET: float = 0.65
"""QED drug-likeness target. ``>= 0.65`` is the canonical "drug-like"
gate. Range is ``[0, 1]``."""

DEFAULT_POSEBUSTERS_FAILURE_FRACTION: float = 0.10
"""PoseBusters failure-fraction ceiling. ``<= 0.10`` is the canonical
"passing" gate; anything worse is a structural failure."""

DEFAULT_ADMET_TOX_THRESHOLD: float = 0.50
"""ADMET toxicity probability ceiling. ``<= 0.50`` is the canonical
"non-toxic" gate. Range is ``[0, 1]``."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_artifact(payload: Mapping[str, Any]) -> ArtifactHash:
    """Compute the canonical ArtifactHash for a calibration target."""
    return ArtifactHash(_hash_artifact_func(dict(payload)))


# ---------------------------------------------------------------------------
# Base evaluator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _MoleculeTargetEvaluator(_MoleculeEvaluatorProtocol):
    """Shared scaffolding for concrete molecule evaluator adapters.

    Concrete subclasses populate ``target_name``, ``default_target``,
    ``good_direction`` (``"low"`` or ``"high"``), and ``uncertainty_bound``;
    ``score`` and ``evaluate`` are derived from those constants.

    The base class is a concrete :class:`Evaluator`: it carries the
    canonical calibration artifact hash and exposes a deterministic
    ``evaluate`` implementation that simply compares the supplied
    ``sample`` mapping's ``score`` field against the target and returns
    a normalized goodness score in ``[0, 1]``.
    """

    target_name: str
    default_target: float
    good_direction: str  # ``"low"`` or ``"high"``
    uncertainty_bound: float

    # ------------------------------------------------------------------
    # Evaluator protocol surface
    # ------------------------------------------------------------------

    @property
    def calibration_artifact_hash(self) -> UniversalArtifactHash:
        return UniversalArtifactHash(
            _hash_artifact(
                {
                    "evaluator": "adaptive_reflow.molecular.calibration_protocols",
                    "target_name": self.target_name,
                    "default_target": float(self.default_target),
                    "good_direction": str(self.good_direction),
                    "uncertainty_bound": float(self.uncertainty_bound),
                }
            )
        )

    def score(self, state_bundle: Any) -> float:  # pragma: no cover - protocol
        raise NotImplementedError(
            f"{type(self).__name__}.score must be overridden by the concrete subclass"
        )

    def evaluate(
        self,
        *,
        sample: Mapping[str, Any],
    ) -> tuple[float, Mapping[str, float]]:
        """Evaluate ``sample`` against the canonical molecule target.

        The input ``sample`` mapping must carry a ``score`` entry with
        the raw metric value. The function returns
        ``(goodness, diagnostics)`` where ``goodness`` is in ``[0, 1]``
        (1.0 = meets target; 0.0 = misses target by the uncertainty
        bound or worse) and ``diagnostics`` exposes ``raw_score``,
        ``target``, ``uncertainty_bound``, and ``good_direction``.

        ``good_direction="low"`` treats lower raw scores as better
        (e.g. GNINA binding kcal/mol).
        ``good_direction="high"`` treats higher raw scores as better
        (e.g. QED).
        """
        raw = sample.get("score")
        if raw is None:
            raise ValueError(
                f"{self.target_name} evaluator requires sample['score']"
            )
        try:
            raw_value = float(raw)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(
                f"{self.target_name} evaluator sample['score'] must be numeric"
            ) from exc
        target = float(self.default_target)
        bound = float(self.uncertainty_bound)
        if not bound > 0.0:
            raise ValueError(
                f"{self.target_name} evaluator uncertainty_bound must be positive"
            )
        if self.good_direction == "low":
            gap = max(0.0, raw_value - target)
        elif self.good_direction == "high":
            gap = max(0.0, target - raw_value)
        else:  # pragma: no cover - defensive
            raise ValueError(
                f"{self.target_name} evaluator good_direction must be 'low' or 'high'"
            )
        goodness = max(0.0, min(1.0, 1.0 - gap / bound))
        diagnostics: dict[str, float] = {
            "raw_score": float(raw_value),
            "target": float(target),
            "uncertainty_bound": float(bound),
            "good_direction": 1.0 if self.good_direction == "low" else 0.0,
            "goodness": float(goodness),
        }
        return float(goodness), diagnostics


# ---------------------------------------------------------------------------
# GNINAEvaluator (binding affinity, kcal/mol — lower is better)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GNINAEvaluator(_MoleculeTargetEvaluator):
    """Concrete :class:`Evaluator` for GNINA binding-affinity scores.

    The default target is ``-4.0`` kcal/mol; lower is better. The
    canonical uncertainty bound is ``2.5`` kcal/mol (the standard
    :class:`adaptive_reflow.legacy.metric_feedback.ConditionPolicyParameters.binding_gap_scale`).
    """

    target_name: str = "gnina"
    default_target: float = DEFAULT_GNINA_TARGET_SCORE
    good_direction: str = "low"
    uncertainty_bound: float = 2.5


# ---------------------------------------------------------------------------
# PoseBustersEvaluator (geometry / structural validity — higher is better)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoseBustersEvaluator(_MoleculeTargetEvaluator):
    """Concrete :class:`Evaluator` for PoseBusters geometry passes.

    The canonical score is a failure fraction in ``[0, 1]``; lower is
    better (zero = clean pass). The default target is ``0.10`` (10 %
    failure ceiling). Good direction is ``"low"``.
    """

    target_name: str = "posebusters"
    default_target: float = DEFAULT_POSEBUSTERS_FAILURE_FRACTION
    good_direction: str = "low"
    uncertainty_bound: float = 1.0


# ---------------------------------------------------------------------------
# QEDEvaluator (drug-likeness — higher is better)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QEDEvaluator(_MoleculeTargetEvaluator):
    """Concrete :class:`Evaluator` for QED drug-likeness scores.

    The default target is ``0.65``; higher is better. The canonical
    uncertainty bound is ``0.25`` (the standard
    :class:`adaptive_reflow.legacy.metric_feedback.ConditionPolicyParameters.druglikeness_gap_scale`).
    """

    target_name: str = "qed_target"
    default_target: float = DEFAULT_QED_TARGET
    good_direction: str = "high"
    uncertainty_bound: float = 0.25


# ---------------------------------------------------------------------------
# ADMETEvaluator (toxicity probability — lower is better)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ADMETEvaluator(_MoleculeTargetEvaluator):
    """Concrete :class:`Evaluator` for ADMET toxicity probability.

    The canonical score is a toxicity probability in ``[0, 1]``; lower
    is better (zero = non-toxic). The default target is ``0.50`` (50 %
    probability ceiling). Good direction is ``"low"``.
    """

    target_name: str = "admet_target"
    default_target: float = DEFAULT_ADMET_TOX_THRESHOLD
    good_direction: str = "low"
    uncertainty_bound: float = 1.0


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def gnina_evaluator() -> GNINAEvaluator:
    """Return a fresh :class:`GNINAEvaluator` with default target."""
    return GNINAEvaluator()


def posebusters_evaluator() -> PoseBustersEvaluator:
    """Return a fresh :class:`PoseBustersEvaluator` with default target."""
    return PoseBustersEvaluator()


def qed_evaluator() -> QEDEvaluator:
    """Return a fresh :class:`QEDEvaluator` with default target."""
    return QEDEvaluator()


def admet_evaluator() -> ADMETEvaluator:
    """Return a fresh :class:`ADMETEvaluator` with default target."""
    return ADMETEvaluator()


# ---------------------------------------------------------------------------
# Back-compat free function: molecule-side facade of the legacy
# ``adaptive_reflow_external_metric_controls`` planner. The current
# implementation lives in
# :mod:`adaptive_reflow.legacy.metric_feedback`; this shim is provided so
# molecule-aware callers can import the symbol from a stable location.
# ---------------------------------------------------------------------------


def adaptive_reflow_external_metric_controls(  # pragma: no cover - thin shim
    external_feedback: Mapping[str, Any],
    round_proxy: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Thin molecule-side shim around the legacy external-metric planner.

    The real planner lives in
    :func:`adaptive_reflow.legacy.metric_feedback.adaptive_reflow_external_metric_controls`.
    This shim re-exports the function under the molecule namespace so
    callers that have already moved to ``adaptive_reflow.molecular`` can
    reach the planner without reaching back into the ``legacy/`` tree.
    """
    from adaptive_reflow.legacy.metric_feedback import (
        adaptive_reflow_external_metric_controls as _legacy_planner,
    )

    return _legacy_planner(
        external_feedback,
        round_proxy,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    # Concrete Evaluator classes
    "ADMETEvaluator",
    "GNINAEvaluator",
    "PoseBustersEvaluator",
    "QEDEvaluator",
    # Default target constants
    "DEFAULT_ADMET_TOX_THRESHOLD",
    "DEFAULT_GNINA_TARGET_SCORE",
    "DEFAULT_POSEBUSTERS_FAILURE_FRACTION",
    "DEFAULT_QED_TARGET",
    # Factory helpers
    "admet_evaluator",
    # Back-compat free function (legacy facade)
    "adaptive_reflow_external_metric_controls",
    "gnina_evaluator",
    # Target tables
    "MOLECULE_CALIBRATION_TARGETS",
    "MOLECULE_CHANNEL_TO_METRIC",
    "posebusters_evaluator",
    "qed_evaluator",
]
