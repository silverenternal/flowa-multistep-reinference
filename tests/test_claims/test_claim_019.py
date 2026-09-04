"""CLM-019: SchedulerProtocol is the canonical first-class scheduler axis.

Asserted by docs/CLAIMS.md:376-398.
The framework exposes nine concrete scheduler families via the registry:
    cosine, constant, linear, exponential, polynomial, sigmoid,
    convergence_adaptive, codimension_sheet, sequential.

We pin that the SCHEDULER_REGISTRY contains all nine names.
"""
from __future__ import annotations

from adaptive_reflow.algorithm.scheduler._core import SCHEDULER_REGISTRY


EXPECTED_NINE = (
    "cosine",
    "constant",
    "linear",
    "exponential",
    "polynomial",
    "sigmoid",
    "convergence_adaptive",
    "codimension_sheet",
    "sequential",
)


def test_claim_019_registry_has_all_nine_canonical_families() -> None:
    for name in EXPECTED_NINE:
        assert name in SCHEDULER_REGISTRY, f"{name} missing from SCHEDULER_REGISTRY"


def test_claim_019_registry_at_least_nine_entries() -> None:
    """The registry has at least nine families (lower-bound, future-proof)."""
    assert len(SCHEDULER_REGISTRY) >= 9
