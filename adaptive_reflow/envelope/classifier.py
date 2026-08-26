"""Envelope classifier helpers — observable extraction + threshold check.

Internal helpers used by :mod:`adaptive_reflow.envelope.manifest`. Not
exposed through the package's public surface.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

from adaptive_reflow.contracts import (
    ComplementBlockerCode,
    EnvelopeLayer,
)

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


def _read_observables(bundle) -> dict[str, object]:
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

    return not (
        (layer.internal_geometry_pass_required and _coerce_bool(obs.get(OBS_GEOMETRY_PASS)) is not True)
        or (
            layer.evaluator_provenance_required
            and _coerce_bool(obs.get(OBS_EVALUATOR_PROVENANCE_PRESENT)) is not True
        )
    )


def _classify_blocker(
    layer: EnvelopeLayer,
    obs: Mapping[str, object],
) -> ComplementBlockerCode:
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
