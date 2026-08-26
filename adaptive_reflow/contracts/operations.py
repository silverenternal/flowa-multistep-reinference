"""Adaptive reflow typed contracts — operation composition (DTB-L2).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .types import DEFAULT_OPERATION_ORDER, OPERATION_STEPS, ArtifactHash, TraceDigest

__all__ = [
    "DEFAULT_OPERATION_ORDER",
    "OPERATION_STEPS",
    "CommutatorResidualDiagnostic",
    "OperationCompositionContract",
]


# ---------------------------------------------------------------------------
# Operation composition (CONTRACTS.md §6) — DTB-L2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationCompositionContract:
    """Operation order contract; the default order is fixed."""

    version: str
    operation_order: tuple[str, ...]
    default_order: tuple[str, ...] = DEFAULT_OPERATION_ORDER
    commutator_residual_tolerance: float = 0.0
    contract_hash: ArtifactHash = field(default=ArtifactHash(""))


@dataclass(frozen=True)
class CommutatorResidualDiagnostic:
    """Diagnostic row produced by an AB-vs-BA paired test."""

    contract_hash: ArtifactHash
    ab_endpoint_digest: TraceDigest
    ba_endpoint_digest: TraceDigest
    residual_norm: float
    within_tolerance: bool
    inputs_digest_ab: ArtifactHash
    inputs_digest_ba: ArtifactHash
    operation_order_version: str
    recorded_at_round: int
