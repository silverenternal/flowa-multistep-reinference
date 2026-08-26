"""Molecule envelope ladder + tail budget (DTB-NC1 / DTB-NC2).

This module is the molecule-specific concrete implementation of the
universal :class:`adaptive_reflow.universal.envelope.EnvelopeCriterion`
Protocol. It is a verbatim copy of the molecule dataclasses currently
living in :mod:`adaptive_reflow.contracts.envelope`.

Module boundary
---------------

* ``MoleculeEnvelopeLayer``, ``MoleculeEnvelopeManifest`` (frozen
  manifest), ``MoleculeEnvelopeClassification``, and ``MoleculeTailBudgetRow``
  are 100% molecule-specific. The universal
  :class:`adaptive_reflow.universal.envelope.EnvelopeCriterion` Protocol
  lives in :mod:`adaptive_reflow.universal.envelope`.
* Stdlib-only: no torch, no other adaptive_reflow imports (besides
  ``contracts``), no I/O.

Public surface
--------------

Pure-data carriers (frozen dataclasses)
    :class:`MoleculeEnvelopeLayer`
    :class:`MoleculeEnvelopeManifest`
    :class:`MoleculeEnvelopeClassification`
    :class:`MoleculeTailBudgetRow`

Validators
    :func:`validate_molecule_envelope_manifest`
    :func:`validate_molecule_tail_budget_row`

Tasks satisfied
---------------

* ``DTB-NC1`` — generic envelope ladder contract (molecule half).
* ``DTB-NC2`` — generic tail-budget / classification surface (molecule half).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from adaptive_reflow.contracts.types import (
    ArtifactHash,
    BundleId,
    ComplementBlockerCode,
    ManifestId,
    RunId,
    SampleId,
    TailBudgetRowId,
)
from adaptive_reflow.contracts.validators import ValidationResult, _ok

# ---------------------------------------------------------------------------
# Envelope ladder (CONTRACTS.md §2) — DTB-NC1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MoleculeEnvelopeLayer:
    """One layer in the run-start frozen compact-envelope ladder.

    All fields are molecule-specific thresholds (no universal counterpart
    carries the same vocabulary). The
    :class:`adaptive_reflow.universal.envelope.EnvelopeCriterion` Protocol
    is the universal surface; this dataclass is its concrete molecule
    implementation.
    """

    layer_index: int
    label: str
    coordinate_extent_rms_max: float
    coordinate_extent_rms_source_stats_hash: ArtifactHash
    pocket_distance_max: float
    pocket_contact_support_min: float
    atom_count_min: int
    atom_count_max: int
    graph_complexity_max: int
    sanitization_required: bool
    valence_rules_hash: ArtifactHash
    pair_entropy_min: float
    pair_entropy_source_stats_hash: ArtifactHash
    projection_loss_max: float
    internal_geometry_pass_required: bool
    evaluator_provenance_required: bool
    source_stats_hash: ArtifactHash
    threshold_digest: ArtifactHash
    layer_hash: ArtifactHash


@dataclass(frozen=True)
class MoleculeEnvelopeManifest:
    """Run-start frozen envelope manifest. ``tail_selection_certified`` is False."""

    manifest_id: ManifestId
    run_id: RunId
    sample_id: SampleId
    target_pocket_hash: ArtifactHash
    config_hash: ArtifactHash
    created_at_round: Literal[0]
    layers: tuple[MoleculeEnvelopeLayer, ...]
    empirical_only: bool
    finite_prefix_only: bool
    tail_selection_certified: Literal[False]
    manifest_hash: ArtifactHash


@dataclass(frozen=True)
class MoleculeEnvelopeClassification:
    """Per-bundle envelope classification; ``complement_blocker`` is first match."""

    bundle_id: BundleId
    matched_layer_index: int | None
    complement_blocker: ComplementBlockerCode | None
    within_layer_thresholds: bool
    residual_extents: Mapping[str, float]


@dataclass(frozen=True)
class MoleculeTailBudgetRow:
    """Per-round tail budget row; ``tail_selection_certified`` is always False."""

    row_id: TailBudgetRowId
    manifest_id: ManifestId
    outer_cycle_id: int
    round_in_cycle: int
    target_round: int
    archive_count: int
    deduplicated_archive_count: int
    deduplicated_transfer_score_mass: float
    requested_restart_write_mass: float
    accepted_restart_write_mass: float
    unknown_complement_mass: float
    missing_evidence_mass: float
    per_layer_excess_mass: Mapping[int, float]
    empirical_only: bool
    finite_prefix_only: bool
    tail_selection_certified: Literal[False]
    ledger_hash: ArtifactHash


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_molecule_envelope_manifest(
    m: MoleculeEnvelopeManifest,
) -> ValidationResult:
    """Validate :class:`MoleculeEnvelopeManifest`.

    Rejects when ``empirical_only`` is not ``True``,
    ``tail_selection_certified`` is not ``False``, ``created_at_round``
    is not ``0``, layers are not strictly monotone by ``layer_index``, or
    ``manifest_hash`` is empty.
    """
    errors: list[str] = []

    if not m.empirical_only:
        errors.append("empirical_only must be True")

    if m.tail_selection_certified is not False:
        errors.append(
            "tail_selection_certified must be False (forbidden to set True); "
            f"got {m.tail_selection_certified!r}"
        )
    if m.created_at_round != 0:
        errors.append(
            f"created_at_round must be exactly 0 (frozen at run start), got {m.created_at_round!r}"
        )
    if not m.manifest_hash:
        errors.append("manifest_hash must be non-empty")
    indices = [layer.layer_index for layer in m.layers]
    for i in range(1, len(indices)):
        if indices[i - 1] >= indices[i]:
            errors.append(
                f"layers must be strictly monotone by layer_index; "
                f"got {indices[i - 1]} >= {indices[i]} at position {i}"
            )
    if errors:
        return (False, tuple(errors))
    return _ok()


def validate_molecule_tail_budget_row(t: MoleculeTailBudgetRow) -> ValidationResult:
    """Validate :class:`MoleculeTailBudgetRow`.

    Rejects when ``empirical_only`` or ``finite_prefix_only`` is not
    ``True``, ``tail_selection_certified`` is not ``False``, or
    ``row_id`` / ``manifest_id`` is empty.
    """
    errors: list[str] = []
    if not t.empirical_only:
        errors.append("empirical_only must be True")
    if not t.finite_prefix_only:
        errors.append("finite_prefix_only must be True")
    if t.tail_selection_certified is not False:
        errors.append(
            "tail_selection_certified must be False (forbidden to set True); "
            f"got {t.tail_selection_certified!r}"
        )
    if not t.row_id:
        errors.append("row_id must be non-empty")
    if not t.manifest_id:
        errors.append("manifest_id must be non-empty")
    if errors:
        return (False, tuple(errors))
    return _ok()


# ---------------------------------------------------------------------------
# Back-compat aliases — the OLD `contracts.envelope` names also exist as
# `MoleculeEnvelope*` re-exports so existing callers that reach for the
# unqualified names (e.g. ``EnvelopeLayer``) keep working once they are
# redirected to import from ``adaptive_reflow.molecular``.
# ---------------------------------------------------------------------------


EnvelopeLayer = MoleculeEnvelopeLayer
EnvelopeManifest = MoleculeEnvelopeManifest
EnvelopeClassification = MoleculeEnvelopeClassification
TailBudgetRow = MoleculeTailBudgetRow
# Historical name used in the old ``contracts.envelope`` module.
FrozenEnvelopeManifest = MoleculeEnvelopeManifest

validate_envelope_manifest = validate_molecule_envelope_manifest
validate_tail_budget_row = validate_molecule_tail_budget_row


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    # Molecule concrete dataclasses
    "MoleculeEnvelopeLayer",
    "MoleculeEnvelopeManifest",
    "MoleculeEnvelopeClassification",
    "MoleculeTailBudgetRow",
    # Back-compat aliases (so callers redirected from
    # ``contracts.envelope`` keep the unqualified names working).
    "EnvelopeLayer",
    "EnvelopeManifest",
    "EnvelopeClassification",
    "TailBudgetRow",
    "FrozenEnvelopeManifest",
    # Validators
    "validate_envelope_manifest",
    "validate_molecule_envelope_manifest",
    "validate_molecule_tail_budget_row",
    "validate_tail_budget_row",
]
