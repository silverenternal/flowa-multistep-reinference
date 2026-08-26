"""Adaptive reflow — pure decision logic (DTB-L3 / DTB-R4 / DTB-L4 calc leg).

Stateless decision logic that is not itself a frame piece (archive selection,
stratification, pruning, noise accounting). No torch; no I/O.
"""
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

__all__ = [
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
