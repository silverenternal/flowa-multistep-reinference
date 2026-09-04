"""Adaptive reflow typed contracts — NewType aliases + literal-set constants.

.. note::
   The four molecule channel aliases (``CoordinateChannelRef`` /
   ``ChargeChannelRef`` / ``RawPairChannelRef`` /
   ``ProjectedPairChannelRef``) and the ``CHANNEL_NAMES`` literal set
   are canonical in :mod:`adaptive_reflow.molecular.channels` (the
   molecule concrete layer). They are re-exported here as
   *placeholder* ``NewType('X', str)`` declarations so existing
   ``from adaptive_reflow.contracts import CoordinateChannelRef``
   imports keep working (the canonical NewTypes are not byte-
   compatible — at runtime both are erased to ``str``). New code
   should import the molecule channel vocabulary from
   :mod:`adaptive_reflow.molecular`:

       from adaptive_reflow.molecular import (
           MOLECULE_CHANNELS,
           CoordinateChannelRef,
           ChargeChannelRef,
           RawPairChannelRef,
           ProjectedPairChannelRef,
       )

   The universal :data:`ChannelName` alias stays in this module because
   it carries no molecule vocabulary.

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NewType

# ---------------------------------------------------------------------------
# NewType aliases (round-trippable) — universal
# ---------------------------------------------------------------------------

BundleId = NewType("BundleId", str)
LedgerRowId = NewType("LedgerRowId", str)
ManifestId = NewType("ManifestId", str)
RunId = NewType("RunId", str)
SampleId = NewType("SampleId", str)
TriggerId = NewType("TriggerId", str)
TraceDigest = NewType("TraceDigest", str)
ConditionDigest = NewType("ConditionDigest", str)
ArtifactHash = NewType("ArtifactHash", str)
MechanismId = NewType("MechanismId", str)
ChannelName = NewType("ChannelName", str)
FeedbackMode = NewType("FeedbackMode", str)
FactorValue = NewType("FactorValue", float)
ComplementBlockerCode = NewType("ComplementBlockerCode", str)
RestartTriggerCode = NewType("RestartTriggerCode", str)
PolicyId = NewType("PolicyId", str)
ProvenanceChain = NewType("ProvenanceChain", tuple)
FrameSpec = NewType("FrameSpec", Mapping[str, Any])
ShapeSpec = NewType("ShapeSpec", Mapping[str, Any])
MaterializationEvidenceRef = NewType("MaterializationEvidenceRef", Mapping[str, Any])
EvaluatorProvenanceRef = NewType("EvaluatorProvenanceRef", Mapping[str, Any])
FeedbackEvidenceRef = NewType("FeedbackEvidenceRef", Mapping[str, Any])
TailBudgetRowId = NewType("TailBudgetRowId", str)

# ---------------------------------------------------------------------------
# Molecule channel aliases (placeholder NewTypes, stdlib-only)
# ---------------------------------------------------------------------------
# The four molecule channel aliases are canonical in
# ``adaptive_reflow.molecular.channels`` (with ``Mapping[str, Any]`` as
# the underlying type). The aliases exported here are *placeholder*
# ``NewType('X', str)`` declarations kept for back-compat so existing
# ``from adaptive_reflow.contracts import CoordinateChannelRef``
# imports keep working. They are intentionally distinct NewTypes from
# the canonical molecule ones: at runtime both are erased, so callers
# that pass the placeholder where the canonical is expected behave
# correctly; at the static-typing layer the two are incompatible, which
# is the desired nudge toward importing from ``adaptive_reflow.molecular``
# for new code.
#
# ``_MOLECULE_CHANNELS`` is the literal tuple of channel names; it is
# hard-coded here as a stdlib-only constant (no eager import of
# ``adaptive_reflow.molecular``) so the ``contracts`` ↔ ``molecular``
# import cycle is broken at the root.
CoordinateChannelRef = NewType("CoordinateChannelRef", str)
ChargeChannelRef = NewType("ChargeChannelRef", str)
RawPairChannelRef = NewType("RawPairChannelRef", str)
ProjectedPairChannelRef = NewType("ProjectedPairChannelRef", str)

_MOLECULE_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
    "raw_pair",
    "projected_pair",
)

# ---------------------------------------------------------------------------
# Molecule vocabulary anchor tables (stdlib-only; no eager molecular import)
# ---------------------------------------------------------------------------
# ``MOLECULE_CALIBRATION_TARGETS`` and ``MOLECULE_CHANNEL_TO_METRIC`` are
# the canonical literal tables that used to live in
# :mod:`adaptive_reflow.molecular.calibration_protocols`. They are now
# canonical here (next to :data:`_MOLECULE_CHANNELS`) so both
# :mod:`adaptive_reflow.molecular.calibration_protocols` and
# :mod:`adaptive_reflow.eval.calibration` can import them from a single
# stdlib-only home, removing the historical ``eval -> molecular``
# coupling. The molecule concrete module and the eval layer both
# re-export them under their historical names for back-compat.


MOLECULE_CALIBRATION_TARGETS: Mapping[str, str] = {
    "binding_affinity_kcal": "gnina",
    "qed": "qed_target",
    "admet_tox_flag": "admet_target",
    "synthesizability": "synth_target",
}
"""Canonical mapping from molecule metric name → legacy evaluator-arm name.

Replaces the legacy ``eval.calibration.PREDECLARED_SAFETY_METRICS``
literal set. Each entry names the *kind* of evaluator arm that produces
a primary score for the metric; the arm itself lives in
:mod:`eval.protocol`.
"""


MOLECULE_CHANNEL_TO_METRIC: Mapping[str, str] = {
    "coordinate": "binding_affinity_kcal",
    "charge": "qed",
    "raw_pair": "admet_tox_flag",
    "projected_pair": "synthesizability",
}
"""Canonical mapping from molecule channel name → metric name.

Replaces the legacy ``eval.calibration.CHANNEL_NAMES_FOR_CALIBRATION``
literal set. The channels are exactly :data:`_MOLECULE_CHANNELS` in the
same order.
"""


# ---------------------------------------------------------------------------
# Channel/feedback/trigger/schedule literal sets (string enums inlined)
# ---------------------------------------------------------------------------

# ``CHANNEL_NAMES`` was historically the canonical four-channel molecule
# vocabulary. The molecule-aware canonical home is
# ``adaptive_reflow.molecular.MOLECULE_CHANNELS``; the alias here keeps
# existing imports (``from adaptive_reflow.contracts import CHANNEL_NAMES``)
# working. The new code should use ``molecular.MOLECULE_CHANNELS``.
CHANNEL_NAMES: tuple[str, ...] = _MOLECULE_CHANNELS
FEEDBACK_MODES: tuple[str, ...] = (
    "inference_external_diagnostic",
    "proxy_only",
    "training_authorized",
)
COMPLEMENT_BLOCKER_CODES: tuple[str, ...] = (
    "out_of_envelope",
    "materialization_failure",
    "geometry_failure",
    "evaluator_provenance_missing",
    "lineage_invalid",
    "unclassified",
)
RESTART_TRIGGER_CODES: tuple[str, ...] = (
    "tail_budget_violation",
    "complement_unclassified",
    "materialization_regression",
    "geometry_regression",
    "calibration_drift",
    "valid_evidence_no_progress",
)
SCHEDULE_FAMILIES: tuple[str, ...] = (
    "constant",
    "linear",
    "cosine_no_restart",
    "cosine_guarded_restart",
    "empirical_learned",
)
SCHEDULE_PHASES: tuple[str, ...] = (
    "high_noise",
    "anneal",
    "low_noise",
    "post_restart",
)
FRESH_NOISE_FLOOR_SOURCES: tuple[str, ...] = (
    "schedule",
    "calibration",
    "manual_override",
)

# Per the brief, the OperationStep, AuthorityMode, and ChannelRule (Callable)
# aliases are not exposed as separate top-level types. They are inlined as
# Literal / Callable expressions where used. The Literal tuples are kept here
# so validators can iterate over the legal values without depending on
# typing.Protocol.
OPERATION_STEPS: tuple[str, ...] = (
    "validate",
    "select",
    "restart_distribution",
    "condition_delta",
    "declared_freeze",
    "native_ODE_solve",
    "endpoint_observation",
)
DEFAULT_OPERATION_ORDER: tuple[str, ...] = OPERATION_STEPS
AUTHORITY_MODES: tuple[str, ...] = (
    "noise_bias_diagnostic_only",
    "noise_bias_legacy_standalone",
    "adaptive_reflow_executable",
    "flowa_core_consumer",
)
