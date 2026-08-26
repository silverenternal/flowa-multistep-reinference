"""Adaptive reflow typed contracts — NewType aliases + literal-set constants.

.. note::
   The four molecule channel aliases (``CoordinateChannelRef`` /
   ``ChargeChannelRef`` / ``RawPairChannelRef`` /
   ``ProjectedPairChannelRef``) and the ``CHANNEL_NAMES`` literal set
   were historically defined here. They are now canonical in
   :mod:`adaptive_reflow.molecular.channels` (the molecule concrete
   layer). They are re-exported here for back-compat so existing
   ``from adaptive_reflow.contracts import CoordinateChannelRef``
   imports keep working.

   New code should import the molecule channel vocabulary from
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
# Molecule channel aliases (lazy re-exported from adaptive_reflow.molecular)
# ---------------------------------------------------------------------------
# The four molecule channel aliases are canonical in
# ``adaptive_reflow.molecular.channels``. They are re-exported here via
# a lazy ``__getattr__`` (defined below) to break the import cycle:
#
#   ``contracts.types`` -> ``molecular.channels`` -> ``molecular.__init__``
#     -> ``molecular.bundle`` -> ``contracts.hashes`` -> ``contracts.types``
#     (in-flight, no name yet)
#
# ``MOLECULE_CHANNELS`` is the literal tuple of channel names; it is
# eagerly resolved (it's just a tuple of strings, not a NewType).
from adaptive_reflow.molecular.channels import (  # noqa: E402
    MOLECULE_CHANNELS as _MOLECULE_CHANNELS,
)

_MOLECULE_CHANNEL_ALIASES = frozenset(
    {
        "CoordinateChannelRef",
        "ChargeChannelRef",
        "RawPairChannelRef",
        "ProjectedPairChannelRef",
    }
)


def __getattr__(name: str) -> Any:  # pragma: no cover - exercised via re-export
    """Lazy-load the molecule channel aliases to break the import cycle."""
    if name in _MOLECULE_CHANNEL_ALIASES:
        from adaptive_reflow.molecular.channels import (
            ChargeChannelRef,
            CoordinateChannelRef,
            ProjectedPairChannelRef,
            RawPairChannelRef,
        )

        # Map the requested name to the molecule alias.
        mapping = {
            "CoordinateChannelRef": CoordinateChannelRef,
            "ChargeChannelRef": ChargeChannelRef,
            "RawPairChannelRef": RawPairChannelRef,
            "ProjectedPairChannelRef": ProjectedPairChannelRef,
        }
        value = mapping[name]
        globals()[name] = value
        return value
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


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
