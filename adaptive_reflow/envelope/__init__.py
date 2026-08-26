"""Runtime envelope + tail-budget machinery (DTB-NC1 + DTB-L3 partial).

Builders, classifiers, and accumulators only. The contract types
(``EnvelopeLayer``, ``FrozenEnvelopeManifest``, ``EnvelopeClassification``,
``TailBudgetRow``) live in :mod:`adaptive_reflow.contracts.envelope`.
"""
from .manifest import (
    EvidenceRowHash,
    FrozenEnvelopeManifestBuilder,
    ManifestBuildError,
    StratifiedTailBudgetRow,
    TailBudgetAccumulator,
    classify_endpoint,
)

__all__ = [
    "EvidenceRowHash",
    "FrozenEnvelopeManifestBuilder",
    "ManifestBuildError",
    "StratifiedTailBudgetRow",
    "TailBudgetAccumulator",
    "classify_endpoint",
]
