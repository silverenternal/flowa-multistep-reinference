"""Envelope manifest builder + complement classifier + tail budget accumulator.

This module satisfies:

* ``DTB-NC1`` — frozen envelope ladder + tail budget + complement gate
* ``DTB-NC2`` — tail admissibility into dynamic transfer weight
* ``DTB-L3`` — per-stratum tail-budget excess mass + branch-count /
  pruning audit ledger row.

It exposes three pure-stdlib classes:

* :class:`FrozenEnvelopeManifestBuilder` — produces a run-start frozen manifest.
* :func:`classify_endpoint` — derives an :class:`EnvelopeClassification` from a
  bundle and the frozen manifest thresholds. No current-round score is read.
* :class:`TailBudgetAccumulator` — accumulates per-round mass into a
  :class:`TailBudgetRow` snapshot. Optionally folds per-stratum excess
  mass + prune audit fields into a :class:`StratifiedTailBudgetRow`.

The literal field ``tail_selection_certified`` is ``Literal[False]`` and is
never set to ``True`` in any code path.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import NewType

from adaptive_reflow.contracts import (
    ArtifactHash,
    BundleId,
    EnvelopeClassification,
    EnvelopeLayer,
    FactorValue,
    FrozenEnvelopeManifest,
    ManifestId,
    RoundResultBundle,
    TailBudgetRow,
    TailBudgetRowId,
    hash_artifact,
)
from adaptive_reflow.policy.stratification import Stratum

from .classifier import (
    _BLOCKER_LINEAGE,
    _BLOCKER_MATERIALIZATION,
    _BLOCKER_OUT_OF_ENVELOPE,
    _BLOCKER_UNCLASSIFIED,
    _coerce_bool,
    _read_observables,
    _within_layer,
)
from .classifier import (
    _classify_blocker as _classify_blocker_internal,
)

# ---------------------------------------------------------------------------
# Local NewType aliases (round-trippable)
# ---------------------------------------------------------------------------

EvidenceRowHash = NewType("EvidenceRowHash", str)


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------


class ManifestBuildError(ValueError):
    """Raised when the manifest builder rejects the supplied layer payload."""


class FrozenEnvelopeManifestBuilder:
    """Build a run-start frozen envelope manifest from a layer sequence.

    The builder never inspects current-round scores; layers are validated
    against type / range invariants and a deterministic ``manifest_hash`` is
    produced from ``(manifest_id, target_pocket_hash, config_hash, layers)``.
    """

    @staticmethod
    def _validate_layers(layers: tuple[EnvelopeLayer, ...]) -> list[str]:
        errors: list[str] = []
        if not layers:
            errors.append("layers must be non-empty")
            return errors

        indices = [int(layer.layer_index) for layer in layers]
        if indices[0] != 0:
            errors.append(f"first layer_index must be 0, got {indices[0]}")
        for i in range(1, len(indices)):
            if indices[i - 1] >= indices[i]:
                errors.append(
                    f"layer_index must be strictly monotone; "
                    f"got {indices[i - 1]} >= {indices[i]} at position {i}"
                )

        for idx, layer in enumerate(layers):
            label_prefix = f"layers[{idx}]"

            rms = float(layer.coordinate_extent_rms_max)
            if not (math.isfinite(rms) and rms > 0.0):
                errors.append(f"{label_prefix}.coordinate_extent_rms_max must be > 0 and finite")

            pocket_d_max = float(layer.pocket_distance_max)
            if not (math.isfinite(pocket_d_max) or math.isinf(pocket_d_max)):
                errors.append(f"{label_prefix}.pocket_distance_max must be finite or +inf")
            elif math.isfinite(pocket_d_max) and pocket_d_max <= 0.0:
                errors.append(f"{label_prefix}.pocket_distance_max must be > 0 or +inf")

            support = float(layer.pocket_contact_support_min)
            if not (math.isfinite(support) and 0.0 <= support <= 1.0):
                errors.append(
                    f"{label_prefix}.pocket_contact_support_min must be in [0, 1]"
                )

            atom_min = int(layer.atom_count_min)
            atom_max = int(layer.atom_count_max)
            if atom_min < 0:
                errors.append(f"{label_prefix}.atom_count_min must be >= 0")
            if atom_max < atom_min:
                errors.append(
                    f"{label_prefix}.atom_count_max ({atom_max}) must be >= "
                    f"atom_count_min ({atom_min})"
                )

            graph_max = int(layer.graph_complexity_max)
            if graph_max < 0:
                errors.append(f"{label_prefix}.graph_complexity_max must be >= 0")

            pair_entropy_min = float(layer.pair_entropy_min)
            if not (math.isfinite(pair_entropy_min) and pair_entropy_min >= 0.0):
                errors.append(f"{label_prefix}.pair_entropy_min must be >= 0 and finite")

            projection_loss_max = float(layer.projection_loss_max)
            if not (math.isfinite(projection_loss_max) and projection_loss_max >= 0.0):
                errors.append(f"{label_prefix}.projection_loss_max must be >= 0 and finite")

            if not str(layer.source_stats_hash):
                errors.append(f"{label_prefix}.source_stats_hash must be non-empty")
            if not str(layer.threshold_digest):
                errors.append(f"{label_prefix}.threshold_digest must be non-empty")
            if not str(layer.layer_hash):
                errors.append(f"{label_prefix}.layer_hash must be non-empty")
            if not str(layer.coordinate_extent_rms_source_stats_hash):
                errors.append(
                    f"{label_prefix}.coordinate_extent_rms_source_stats_hash must be non-empty"
                )
            if not str(layer.pair_entropy_source_stats_hash):
                errors.append(
                    f"{label_prefix}.pair_entropy_source_stats_hash must be non-empty"
                )
            if not str(layer.valence_rules_hash):
                errors.append(f"{label_prefix}.valence_rules_hash must be non-empty")
        return errors

    def build(
        self,
        target_pocket_hash: ArtifactHash,
        config_hash: ArtifactHash,
        layers: tuple[EnvelopeLayer, ...],
    ) -> FrozenEnvelopeManifest:
        """Return a frozen manifest. Raises :class:`ManifestBuildError` on bad input.

        ``run_id`` and ``sample_id`` are intentionally absent from this
        signature per the brief; the caller is expected to thread them via the
        :func:`dataclasses.replace` constructor or attach them at a higher
        orchestration layer. The builder fills them with empty ``NewType``
        placeholders that downstream validators can overwrite.
        """
        if not str(target_pocket_hash):
            raise ManifestBuildError("target_pocket_hash must be non-empty")
        if not str(config_hash):
            raise ManifestBuildError("config_hash must be non-empty")

        errors = self._validate_layers(layers)
        if errors:
            raise ManifestBuildError("; ".join(errors))

        # Derive manifest_id from (target_pocket_hash, config_hash, layers).
        manifest_id = ManifestId(
            hash_artifact(
                {
                    "target_pocket_hash": str(target_pocket_hash),
                    "config_hash": str(config_hash),
                    "layers": [
                        {
                            "layer_index": int(layer.layer_index),
                            "layer_hash": str(layer.layer_hash),
                            "label": str(layer.label),
                        }
                        for layer in layers
                    ],
                }
            )
        )

        manifest_hash_payload = {
            "manifest_id": str(manifest_id),
            "target_pocket_hash": str(target_pocket_hash),
            "config_hash": str(config_hash),
            "layers": [
                {
                    "layer_index": int(layer.layer_index),
                    "layer_hash": str(layer.layer_hash),
                    "label": str(layer.label),
                    "coordinate_extent_rms_max": float(layer.coordinate_extent_rms_max),
                    "pocket_distance_max": float(layer.pocket_distance_max),
                    "pocket_contact_support_min": float(layer.pocket_contact_support_min),
                    "atom_count_min": int(layer.atom_count_min),
                    "atom_count_max": int(layer.atom_count_max),
                    "graph_complexity_max": int(layer.graph_complexity_max),
                    "pair_entropy_min": float(layer.pair_entropy_min),
                    "projection_loss_max": float(layer.projection_loss_max),
                    "internal_geometry_pass_required": bool(layer.internal_geometry_pass_required),
                    "evaluator_provenance_required": bool(layer.evaluator_provenance_required),
                    "source_stats_hash": str(layer.source_stats_hash),
                    "threshold_digest": str(layer.threshold_digest),
                }
                for layer in layers
            ],
        }
        manifest_hash = hash_artifact(manifest_hash_payload)

        return FrozenEnvelopeManifest(
            manifest_id=manifest_id,
            run_id=RunIdPlaceholder,
            sample_id=SampleIdPlaceholder,
            target_pocket_hash=target_pocket_hash,
            config_hash=config_hash,
            created_at_round=0,
            layers=layers,
            empirical_only=True,
            finite_prefix_only=True,
            tail_selection_certified=False,
            manifest_hash=manifest_hash,
        )


# Placeholder identities; the manifest builder does not take run_id / sample_id
# per the brief. Downstream orchestration is expected to overwrite these with
# the actual run / sample identifiers via ``dataclasses.replace``.
RunIdPlaceholder = ""
SampleIdPlaceholder = ""


# ---------------------------------------------------------------------------
# Complement classifier
# ---------------------------------------------------------------------------


def classify_endpoint(
    bundle: RoundResultBundle,
    manifest: FrozenEnvelopeManifest,
) -> EnvelopeClassification:
    """Classify ``bundle`` against the static thresholds on ``manifest``.

    No current-round score is consulted. Evidence flags are checked first in a
    fixed deterministic order; if any evidence flag rejects the bundle, the
    classification is the corresponding complement blocker and the endpoint is
    considered "not within" any layer threshold. Only evidence-clean bundles
    may match a layer; the first layer whose thresholds the endpoint satisfies
    wins. If no layer matches an evidence-clean bundle, the endpoint is
    classified as the ``out_of_envelope`` (or ``unclassified`` when layers
    are empty) complement.
    """
    obs = _read_observables(bundle)

    # Evidence flags checked first, in the canonical blocker order. Each one
    # is independent of the layer thresholds: a bundle with a broken lineage,
    # failed materialization, failed geometry, or missing provenance is
    # rejected regardless of which layer it would otherwise fit.
    if _coerce_bool(obs.get("lineage_detached")) is False:
        return EnvelopeClassification(
            bundle_id=bundle.bundle_id,
            matched_layer_index=None,
            complement_blocker=_BLOCKER_LINEAGE,
            within_layer_thresholds=False,
            residual_extents={},
        )

    mat_pass = _coerce_bool(obs.get("materialization_pass"))
    if mat_pass is False:
        return EnvelopeClassification(
            bundle_id=bundle.bundle_id,
            matched_layer_index=None,
            complement_blocker=_BLOCKER_MATERIALIZATION,
            within_layer_thresholds=False,
            residual_extents={},
        )

    for layer in manifest.layers:
        if _within_layer(layer, obs):
            return EnvelopeClassification(
                bundle_id=bundle.bundle_id,
                matched_layer_index=int(layer.layer_index),
                complement_blocker=None,
                within_layer_thresholds=True,
                residual_extents={},
            )

    # Layers exhausted without a match. If the outermost layer requires
    # geometry / provenance, the missing-evidence variant of those blockers
    # may still apply; otherwise the bundle is out-of-envelope.
    if manifest.layers:
        blocker = _classify_blocker_internal(manifest.layers[-1], obs)
        if blocker == _BLOCKER_OUT_OF_ENVELOPE and not manifest.layers[-1].evaluator_provenance_required:
            # No evaluator required and no threshold matched -> out_of_envelope.
            pass
    else:
        blocker = _BLOCKER_UNCLASSIFIED

    return EnvelopeClassification(
        bundle_id=bundle.bundle_id,
        matched_layer_index=None,
        complement_blocker=blocker,
        within_layer_thresholds=False,
        residual_extents={},
    )


# ---------------------------------------------------------------------------
# Tail budget accumulator
# ---------------------------------------------------------------------------


class TailBudgetAccumulator:
    """Per-cycle accumulator that emits a :class:`TailBudgetRow` snapshot."""

    def __init__(self) -> None:
        self._bundle_ids: set[BundleId] = set()
        self._archive_count: int = 0
        self._deduplicated_archive_count: int = 0
        self._deduplicated_transfer_score_mass: float = 0.0
        self._requested_restart_write_mass: float = 0.0
        self._accepted_restart_write_mass: float = 0.0
        self._unknown_complement_mass: float = 0.0
        self._missing_evidence_mass: float = 0.0
        self._per_layer_excess_mass: dict[int, float] = defaultdict(float)
        self._seen_evidence_rows: set[tuple[BundleId, EvidenceRowHash]] = set()
        self._duplicate_evidence_rows_count: int = 0
        # DTB-L3 stratified state:
        self._per_stratum_excess_mass: dict[Stratum, float] = defaultdict(float)
        self._stratified_branch_count: int = 0
        self._stratified_worst_gap: float = 0.0
        self._stratified_worst_error: float = 0.0
        self._prune_reason_codes: tuple[str, ...] = ()

    def update(
        self,
        endpoint_classification: EnvelopeClassification,
        transfer_score_mass: float = 0.0,
        requested_write_mass: float = 0.0,
        accepted_write_mass: float = 0.0,
        missing_evidence_mass: float = 0.0,
        evidence_row_hash: EvidenceRowHash | str = "",
    ) -> None:
        """Fold one endpoint's contribution into the accumulator state."""
        bundle_id = endpoint_classification.bundle_id

        self._archive_count += 1
        if bundle_id not in self._bundle_ids:
            self._bundle_ids.add(bundle_id)
            self._deduplicated_archive_count += 1
            # Distinct bundle -> add to deduplicated transfer-score mass.
            self._deduplicated_transfer_score_mass += float(transfer_score_mass)
        # else: duplicate bundle_id -> transfer-score mass does NOT inflate.

        self._requested_restart_write_mass += float(requested_write_mass)
        self._accepted_restart_write_mass += float(accepted_write_mass)
        self._missing_evidence_mass += float(missing_evidence_mass)

        if not endpoint_classification.within_layer_thresholds:
            self._unknown_complement_mass += float(transfer_score_mass)

        # Per-layer excess mass: every out-of-envelope endpoint charges the
        # outermost layer's excess bucket by the transfer score mass.
        # (Layers may legitimately hold non-negative values for matched bundles
        # too; we only charge excess for unmatched endpoints.)
        if not endpoint_classification.within_layer_thresholds:
            # Matched layer index is None; charge layer_index 0 as the default
            # per-layer bucket placeholder. The manifest itself does not carry
            # this counter; it is recorded for diagnostic reproducibility.
            self._per_layer_excess_mass[0] += float(transfer_score_mass)

        # Duplicate evidence row accounting (does not inflate mass).
        if evidence_row_hash:
            key = (bundle_id, EvidenceRowHash(str(evidence_row_hash)))
            if key in self._seen_evidence_rows:
                self._duplicate_evidence_rows_count += 1
            else:
                self._seen_evidence_rows.add(key)

    def record_stratum_excess_mass(self, stratum: Stratum, mass: float) -> None:
        """Fold one stratum's excess-mass contribution into the accumulator.

        Missing-mass / unallocated strata are not added; the snapshot's
        :attr:`StratifiedTailBudgetRow.per_stratum_excess_mass` only lists
        strata that actually received mass, keeping the ledger reproducible
        from the offline history.
        """
        if not isinstance(stratum, Stratum):
            raise ValueError(
                f"stratum must be a Stratum member, got {stratum!r}"
            )
        f = float(mass)
        if not math.isfinite(f):
            raise ValueError(f"mass must be finite, got {mass!r}")
        if f < 0.0:
            raise ValueError(f"mass must be >= 0, got {f!r}")
        self._per_stratum_excess_mass[stratum] += f

    def record_stratified_audit(
        self,
        branch_count: int,
        gap: FactorValue,
        calibrated_error: FactorValue,
        prune_reason_codes: Iterable[str] = (),
    ) -> None:
        """Fold a stratified prune audit into the accumulator.

        The branch_count, worst-case gap, worst-case calibrated error and
        prune reason codes are accumulated across the round; the snapshot
        reports the *worst-case* (max) values seen, matching the
        ``UnorderedAuditResult`` contract from :mod:`pruning_gate`.
        """
        if isinstance(branch_count, bool) or not isinstance(branch_count, int):
            raise ValueError(
                f"branch_count must be int, got {type(branch_count).__name__}"
            )
        if branch_count < 0:
            raise ValueError(f"branch_count must be >= 0, got {branch_count}")
        g = float(gap)
        if not math.isfinite(g) or g < 0.0:
            raise ValueError(f"gap must be finite and >= 0, got {gap!r}")
        e = float(calibrated_error)
        if not math.isfinite(e) or e < 0.0:
            raise ValueError(
                f"calibrated_error must be finite and >= 0, got "
                f"{calibrated_error!r}"
            )

        self._stratified_branch_count += int(branch_count)
        self._stratified_worst_gap = max(self._stratified_worst_gap, g)
        self._stratified_worst_error = max(self._stratified_worst_error, e)
        # Reason codes are appended in arrival order. The full round-level
        # tuple is what the offline ledger carries.
        self._prune_reason_codes = self._prune_reason_codes + tuple(
            str(c) for c in prune_reason_codes
        )

    def snapshot(
        self,
        manifest: FrozenEnvelopeManifest,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> TailBudgetRow:
        """Emit a :class:`TailBudgetRow` with the current accumulator state."""
        row_id = TailBudgetRowId(
            hash_artifact(
                {
                    "manifest_id": str(manifest.manifest_id),
                    "outer_cycle_id": int(outer_cycle_id),
                    "round_in_cycle": int(round_in_cycle),
                    "target_round": int(target_round),
                    "deduplicated_archive_count": self._deduplicated_archive_count,
                    "archive_count": self._archive_count,
                    "deduplicated_transfer_score_mass": self._deduplicated_transfer_score_mass,
                    "duplicate_evidence_rows_count": self._duplicate_evidence_rows_count,
                }
            )
        )
        ledger_hash = hash_artifact(
            {
                "row_id": str(row_id),
                "manifest_id": str(manifest.manifest_id),
                "requested_restart_write_mass": self._requested_restart_write_mass,
                "accepted_restart_write_mass": self._accepted_restart_write_mass,
                "unknown_complement_mass": self._unknown_complement_mass,
                "missing_evidence_mass": self._missing_evidence_mass,
                "per_layer_excess_mass": {
                    str(k): float(v) for k, v in sorted(self._per_layer_excess_mass.items())
                },
            }
        )

        return TailBudgetRow(
            row_id=row_id,
            manifest_id=manifest.manifest_id,
            outer_cycle_id=int(outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            target_round=int(target_round),
            archive_count=self._archive_count,
            deduplicated_archive_count=self._deduplicated_archive_count,
            deduplicated_transfer_score_mass=self._deduplicated_transfer_score_mass,
            requested_restart_write_mass=self._requested_restart_write_mass,
            accepted_restart_write_mass=self._accepted_restart_write_mass,
            unknown_complement_mass=self._unknown_complement_mass,
            missing_evidence_mass=self._missing_evidence_mass,
            per_layer_excess_mass=dict(self._per_layer_excess_mass),
            empirical_only=True,
            finite_prefix_only=True,
            tail_selection_certified=False,
            ledger_hash=ledger_hash,
        )

    def stratified_snapshot(
        self,
        manifest: FrozenEnvelopeManifest,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> StratifiedTailBudgetRow:
        """Emit a :class:`StratifiedTailBudgetRow` with the accumulated DTB-L3 state.

        Convenience wrapper around :meth:`snapshot` that folds in the
        stratified state accumulated via :meth:`record_stratum_excess_mass`
        and :meth:`record_stratified_audit`. The base :class:`TailBudgetRow`
        remains the canonical envelope-level row; the stratified wrapper
        carries the per-stratum excess mass, branch count, gap, calibrated
        error and prune reason codes that ``pruning_gate`` emits.
        """
        base_row = self.snapshot(
            manifest=manifest,
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=round_in_cycle,
            target_round=target_round,
        )
        return StratifiedTailBudgetRow(
            base_row=base_row,
            per_stratum_excess_mass=dict(self._per_stratum_excess_mass),
            branch_count=int(self._stratified_branch_count),
            gap=FactorValue(float(self._stratified_worst_gap)),
            calibrated_error=FactorValue(float(self._stratified_worst_error)),
            prune_reason_codes=self._prune_reason_codes,
        )

    def reset_cycle(self) -> None:
        """Reset accumulator state for a new outer cycle."""
        self._bundle_ids.clear()
        self._archive_count = 0
        self._deduplicated_archive_count = 0
        self._deduplicated_transfer_score_mass = 0.0
        self._requested_restart_write_mass = 0.0
        self._accepted_restart_write_mass = 0.0
        self._unknown_complement_mass = 0.0
        self._missing_evidence_mass = 0.0
        self._per_layer_excess_mass = defaultdict(float)
        self._seen_evidence_rows.clear()
        self._duplicate_evidence_rows_count = 0
        # DTB-L3 stratified reset.
        self._per_stratum_excess_mass = defaultdict(float)
        self._stratified_branch_count = 0
        self._stratified_worst_gap = 0.0
        self._stratified_worst_error = 0.0
        self._prune_reason_codes = ()


# ---------------------------------------------------------------------------
# Stratified tail budget (DTB-L3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StratifiedTailBudgetRow:
    """DTB-L3 stratified extension of :class:`TailBudgetRow`.

    Carries the per-stratum excess mass, the branch-count, the worst-case
    dominance gap and calibrated error, and the prune reason codes. The
    row is reproducible from the offline ledger because every field is a
    pure function of the accumulator's stratified inputs plus the
    underlying :class:`TailBudgetRow`.

    The literal field ``tail_selection_certified`` remains ``Literal[False]``
    — DTB-L3 never upgrades the row to a tail certificate.

    Attributes
    ----------
    base_row:
        The underlying :class:`TailBudgetRow` carrying the envelope-level
        tail budget fields.
    per_stratum_excess_mass:
        Mapping ``Stratum -> excess mass``. Strata that never received
        any excess mass are absent; the field never inflates missing
        strata with a zero entry.
    branch_count:
        Number of candidate branches the gate saw for this row (stratified
        candidates + pruned branches). ``>= 0``.
    gap:
        Worst-case dominance gap observed across the surviving per-stratum
        dominant branches. ``FactorValue``.
    calibrated_error:
        Worst-case calibrated error observed across the surviving
        per-stratum dominant branches. ``FactorValue``.
    prune_reason_codes:
        Tuple of human-readable reason codes, one per branch in the
        canonical deterministic ordering. Never parsed.
    """

    base_row: TailBudgetRow
    per_stratum_excess_mass: Mapping[Stratum, float]
    branch_count: int
    gap: FactorValue
    calibrated_error: FactorValue
    prune_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.branch_count, int) or isinstance(
            self.branch_count, bool
        ):
            raise ValueError(
                f"branch_count must be int, got {type(self.branch_count).__name__}"
            )
        if self.branch_count < 0:
            raise ValueError(
                f"branch_count must be >= 0, got {self.branch_count}"
            )
        gap = float(self.gap)
        if not math.isfinite(gap) or gap < 0.0:
            raise ValueError(f"gap must be finite and >= 0, got {gap!r}")
        err = float(self.calibrated_error)
        if not math.isfinite(err) or err < 0.0:
            raise ValueError(
                f"calibrated_error must be finite and >= 0, got "
                f"{err!r}"
            )
        # per_stratum_excess_mass keys must be valid Stratum members; any
        # unknown key fails closed to keep the ledger reproducible.
        for stratum in self.per_stratum_excess_mass:
            if not isinstance(stratum, Stratum):
                raise ValueError(
                    "per_stratum_excess_mass keys must be Stratum members, "
                    f"got {stratum!r}"
                )

    def ledger_payload(self) -> Mapping[str, object]:
        """Return a JSON-serializable dict for offline-ledger replay."""
        return {
            "base_row_id": str(self.base_row.row_id),
            "per_stratum_excess_mass": {
                stratum.value: float(mass)
                for stratum, mass in sorted(
                    self.per_stratum_excess_mass.items(),
                    key=lambda kv: kv[0].value,
                )
            },
            "branch_count": int(self.branch_count),
            "gap": float(self.gap),
            "calibrated_error": float(self.calibrated_error),
            "prune_reason_codes": list(self.prune_reason_codes),
        }

    def ledger_hash(self) -> ArtifactHash:
        """Return the deterministic sha256 of :meth:`ledger_payload`."""
        return hash_artifact(self.ledger_payload())
