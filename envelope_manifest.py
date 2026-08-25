"""Envelope manifest, complement classifier, and tail budget accumulator.

This module satisfies:

* ``DTB-NC1`` — frozen envelope ladder + tail budget + complement gate
* ``DTB-NC2`` — tail admissibility into dynamic transfer weight

It exposes three pure-stdlib classes:

* :class:`FrozenEnvelopeManifestBuilder` — produces a run-start frozen manifest.
* :func:`classify_endpoint` — derives an :class:`EnvelopeClassification` from a
  bundle and the frozen manifest thresholds. No current-round score is read.
* :class:`TailBudgetAccumulator` — accumulates per-round mass into a
  :class:`TailBudgetRow` snapshot.

The literal field ``tail_selection_certified`` is ``Literal[False]`` and is
never set to ``True`` in any code path.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping, NewType

from .restart_memory_types import (
    ArtifactHash,
    BundleId,
    ComplementBlockerCode,
    EnvelopeClassification,
    EnvelopeLayer,
    FrozenEnvelopeManifest,
    ManifestId,
    RoundResultBundle,
    TailBudgetRow,
    TailBudgetRowId,
    hash_artifact,
)


# ---------------------------------------------------------------------------
# Local NewType aliases (round-trippable)
# ---------------------------------------------------------------------------

EvidenceRowHash = NewType("EvidenceRowHash", str)


# ---------------------------------------------------------------------------
# Observable fields on a RoundResultBundle that the classifier can read
# ---------------------------------------------------------------------------

# Mapping keys we read from coordinate_channel / charge_channel / shape_spec.
# Missing keys are treated as "unknown" and resolve to a complement blocker.
OBS_COORDINATE_EXTENT_RMS = "coordinate_extent_rms"
OBS_POCKET_DISTANCE = "pocket_distance"
OBS_POCKET_CONTACT_SUPPORT = "pocket_contact_support"
OBS_ATOM_COUNT = "atom_count"
OBS_GRAPH_COMPLEXITY = "graph_complexity"
OBS_PAIR_ENTROPY = "pair_entropy"
OBS_PROJECTION_LOSS = "projection_loss"
OBS_MATERIALIZATION_PASS = "materialization_pass"
OBS_GEOMETRY_PASS = "geometry_pass"
OBS_EVALUATOR_PROVENANCE_PRESENT = "evaluator_provenance_present"
OBS_LINEAGE_DETACHED = "lineage_detached"

_BLOCKER_UNCLASSIFIED: ComplementBlockerCode = ComplementBlockerCode("unclassified")
_BLOCKER_OUT_OF_ENVELOPE: ComplementBlockerCode = ComplementBlockerCode("out_of_envelope")
_BLOCKER_MATERIALIZATION: ComplementBlockerCode = ComplementBlockerCode("materialization_failure")
_BLOCKER_GEOMETRY: ComplementBlockerCode = ComplementBlockerCode("geometry_failure")
_BLOCKER_EVAL_PROVENANCE: ComplementBlockerCode = ComplementBlockerCode("evaluator_provenance_missing")
_BLOCKER_LINEAGE: ComplementBlockerCode = ComplementBlockerCode("lineage_invalid")


# ---------------------------------------------------------------------------
# Observable extraction (defensive; missing fields are None, not exceptions)
# ---------------------------------------------------------------------------


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        if math.isfinite(f):
            return f
    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    return None


def _coerce_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _read_observables(bundle: RoundResultBundle) -> dict[str, object]:
    """Collect observable fields from a bundle. Missing fields stay missing."""
    obs: dict[str, object] = {}

    coord = bundle.coordinate_channel
    if isinstance(coord, Mapping):
        for key in (OBS_COORDINATE_EXTENT_RMS, OBS_POCKET_DISTANCE, OBS_POCKET_CONTACT_SUPPORT):
            if key in coord:
                obs[key] = coord[key]

    for src, mapping in (
        ("shape_spec", bundle.shape_spec),
        ("frame_spec", bundle.frame_spec),
    ):
        if isinstance(mapping, Mapping):
            for key in (OBS_ATOM_COUNT, OBS_GRAPH_COMPLEXITY):
                if key in mapping and key not in obs:
                    obs[key] = mapping[key]
            # Charge / pair channels may carry atom_count / graph_complexity
            if src == "shape_spec":
                pass

    for mapping in (bundle.charge_channel, bundle.raw_pair_channel, bundle.projected_pair_channel):
        if isinstance(mapping, Mapping):
            for key in (OBS_GRAPH_COMPLEXITY, OBS_PAIR_ENTROPY, OBS_PROJECTION_LOSS):
                if key in mapping and key not in obs:
                    obs[key] = mapping[key]

    if isinstance(bundle.materialization_evidence, Mapping):
        for key in (OBS_MATERIALIZATION_PASS, OBS_GEOMETRY_PASS):
            if key in bundle.materialization_evidence:
                obs[key] = bundle.materialization_evidence[key]

    obs[OBS_EVALUATOR_PROVENANCE_PRESENT] = bundle.evaluator_provenance is not None
    obs[OBS_LINEAGE_DETACHED] = bool(bundle.state_lock_is_detached)
    return obs


def _within_layer(layer: EnvelopeLayer, obs: Mapping[str, object]) -> bool:
    """Return True iff ``obs`` satisfies every threshold on ``layer``.

    Missing observable fields cause the layer to *fail* (strict ordering: the
    envelope is fail-closed when evidence is incomplete).
    """
    rms = _coerce_float(obs.get(OBS_COORDINATE_EXTENT_RMS))
    if rms is None or rms > float(layer.coordinate_extent_rms_max):
        return False

    pocket_d = _coerce_float(obs.get(OBS_POCKET_DISTANCE))
    if pocket_d is None:
        return False
    pocket_d_max = float(layer.pocket_distance_max)
    if math.isinf(pocket_d_max):
        pass  # +inf means "not bounded"
    elif pocket_d > pocket_d_max:
        return False

    support = _coerce_float(obs.get(OBS_POCKET_CONTACT_SUPPORT))
    if support is None or support < float(layer.pocket_contact_support_min):
        return False

    atom_count = _coerce_int(obs.get(OBS_ATOM_COUNT))
    if atom_count is None:
        return False
    if atom_count < int(layer.atom_count_min) or atom_count > int(layer.atom_count_max):
        return False

    graph_c = _coerce_int(obs.get(OBS_GRAPH_COMPLEXITY))
    if graph_c is None or graph_c > int(layer.graph_complexity_max):
        return False

    pair_entropy = _coerce_float(obs.get(OBS_PAIR_ENTROPY))
    if pair_entropy is None or pair_entropy < float(layer.pair_entropy_min):
        return False

    proj_loss = _coerce_float(obs.get(OBS_PROJECTION_LOSS))
    if proj_loss is None or proj_loss > float(layer.projection_loss_max):
        return False

    if layer.internal_geometry_pass_required:
        if _coerce_bool(obs.get(OBS_GEOMETRY_PASS)) is not True:
            return False

    if layer.evaluator_provenance_required:
        if _coerce_bool(obs.get(OBS_EVALUATOR_PROVENANCE_PRESENT)) is not True:
            return False

    return True


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


def _classify_blocker(layer: EnvelopeLayer, obs: Mapping[str, object]) -> ComplementBlockerCode:
    """Return the first matching blocker for ``obs`` against ``layer``.

    Order is deterministic:

    1. ``lineage_invalid`` if the endpoint is not detached.
    2. ``materialization_failure`` if the materialization flag is False.
    3. ``geometry_failure`` if the layer requires geometry and it failed.
    4. ``evaluator_provenance_missing`` if the layer requires provenance.
    5. ``out_of_envelope`` otherwise (threshold breach).
    """
    if _coerce_bool(obs.get(OBS_LINEAGE_DETACHED)) is False:
        return _BLOCKER_LINEAGE

    mat_pass = _coerce_bool(obs.get(OBS_MATERIALIZATION_PASS))
    if mat_pass is False:
        return _BLOCKER_MATERIALIZATION

    if layer.internal_geometry_pass_required:
        geo_pass = _coerce_bool(obs.get(OBS_GEOMETRY_PASS))
        if geo_pass is False:
            return _BLOCKER_GEOMETRY

    if layer.evaluator_provenance_required:
        prov_present = _coerce_bool(obs.get(OBS_EVALUATOR_PROVENANCE_PRESENT))
        if prov_present is False:
            return _BLOCKER_EVAL_PROVENANCE

    return _BLOCKER_OUT_OF_ENVELOPE


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
    if _coerce_bool(obs.get(OBS_LINEAGE_DETACHED)) is False:
        return EnvelopeClassification(
            bundle_id=bundle.bundle_id,
            matched_layer_index=None,
            complement_blocker=_BLOCKER_LINEAGE,
            within_layer_thresholds=False,
            residual_extents={},
        )

    mat_pass = _coerce_bool(obs.get(OBS_MATERIALIZATION_PASS))
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
        blocker = _classify_blocker(manifest.layers[-1], obs)
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


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "EvidenceRowHash",
    "FrozenEnvelopeManifestBuilder",
    "ManifestBuildError",
    "TailBudgetAccumulator",
    "classify_endpoint",
]