"""Adaptive reflow — pure decision logic (DTB-L3 / DTB-R4 / DTB-L4 calc leg).

Stateless decision logic that is not itself a frame piece (archive selection,
stratification, pruning, noise accounting). No torch; no I/O.
"""
from __future__ import annotations

from typing import Any

from .archive import (
    ArchiveEntry,
    CandidateArchiveError,
    CandidateArchiveLineageError,
    CandidateArchiveValidationError,
    SameSampleArchive,
)
from .noise_mass import (
    ERR_BETA_INPUT_INVALID,
    ERR_CURVE_ENTRY_NOT_FINITE,
    ERR_CURVE_NOT_SEQUENCE,
    ERR_PROXY_INPUT_INVALID,
    ERR_SPECTRAL_INPUT_INVALID,
    RMS_preserving_mixing_coefficient,
    ThreeWayDistinction,
    adversarial_stagnation_test,
    exact_spectral_variance,
    physical_noise_proxy,
)
from .pruning import (
    PruneDecision,
    PruneGate,
    UnorderedAuditResult,
)
from .stratification import (
    Stratum,
    StratumAssignment,
    cross_stratum_mix_rejected,
    dominance_ratio,
)

# DTB-R0 §3 case 2 audit / floor constants live in
# :mod:`adaptive_reflow.frame.channel_rule`. We re-export them under
# :mod:`adaptive_reflow.policy` for callers that historically reach
# into the ``policy`` namespace, but the import is deliberately lazy
# to avoid a ``policy`` -> ``frame`` -> ``orchestrator`` -> ``envelope``
# -> ``policy`` cycle.
_FRAME_REEXPORT = frozenset({"AUDIT_STABILITY_COLLAPSE", "PERTURBATION_STABILITY_FLOOR"})

# DTB-R0 §3 case 5 audit code (source revocation) lives in
# :mod:`adaptive_reflow.contracts.validators` and is re-exported here
# for callers that reach into the ``policy`` namespace. Lazy-loaded
# to keep ``policy`` free of eager ``contracts`` imports that could
# re-introduce the molecule-import cycle.
_CONTRACTS_REEXPORT = frozenset({"AUDIT_SOURCE_REVOKED"})


def __getattr__(name: str) -> Any:
    """Lazy-load DTB-R0 §3 re-exports.

    * ``AUDIT_STABILITY_COLLAPSE`` / ``PERTURBATION_STABILITY_FLOOR`` from
      :mod:`frame.channel_rule` (case 2).
    * ``AUDIT_SOURCE_REVOKED`` from :mod:`contracts` (case 5).
    """
    if name in _FRAME_REEXPORT:
        from ..frame import channel_rule as _channel_rule  # noqa: PLC0415

        value = getattr(_channel_rule, name)
        globals()[name] = value
        return value
    if name in _CONTRACTS_REEXPORT:
        from .. import contracts as _contracts  # noqa: PLC0415

        value = getattr(_contracts, name)
        globals()[name] = value
        return value
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


__all__ = [
    # DTB-R0 §3 case 2 audit / floor (re-exported from frame.channel_rule).
    "AUDIT_STABILITY_COLLAPSE",
    "PERTURBATION_STABILITY_FLOOR",
    # DTB-R0 §3 case 5 audit (re-exported from contracts).
    "AUDIT_SOURCE_REVOKED",
    "ERR_BETA_INPUT_INVALID",
    "ERR_CURVE_ENTRY_NOT_FINITE",
    "ERR_CURVE_NOT_SEQUENCE",
    "ERR_PROXY_INPUT_INVALID",
    "ERR_SPECTRAL_INPUT_INVALID",
    # archive
    "ArchiveEntry",
    "CandidateArchiveError",
    "CandidateArchiveLineageError",
    "CandidateArchiveValidationError",
    # pruning
    "PruneDecision",
    "PruneGate",
    "RMS_preserving_mixing_coefficient",
    "SameSampleArchive",
    # stratification
    "Stratum",
    "StratumAssignment",
    "ThreeWayDistinction",
    "UnorderedAuditResult",
    "adversarial_stagnation_test",
    "cross_stratum_mix_rejected",
    "dominance_ratio",
    "exact_spectral_variance",
    # noise mass
    "physical_noise_proxy",
]
