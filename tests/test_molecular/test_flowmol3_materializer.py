"""Pytest suite for :class:`ConcreteFlowMol3Materializer` (D2 — FlowMol3 roundtrip)."""

from __future__ import annotations

import json

import pytest

from adaptive_reflow.molecular.materializer import (
    FLOWMOL3_ENVELOPE_KEYS,
    ConcreteFlowMol3Materializer,
    default_flowmol3_materializer,
)
from adaptive_reflow.universal.materialization import (
    NativeStateBundle,
)


def _make_native(
    atom_count: int,
    *,
    raw_pair_histogram: list[int] | None = None,
    source_round: int = 1,
    source_digest: str = "d-flowmol3",
) -> NativeStateBundle:
    channels: dict[str, str] = {
        "coordinate": "flowmol3:coord:abc",
        "charge": "flowmol3:charge:abc",
        "raw_pair": (
            json.dumps(raw_pair_histogram)
            if raw_pair_histogram is not None
            else "flowmol3:raw_pair:abc"
        ),
    }
    return NativeStateBundle(
        channels=channels,
        atom_count=atom_count,
        backend_kind="flowmol3",
        source_round=source_round,
        source_digest=source_digest,
    )


def test_atoms_count_round_trips() -> None:
    m = default_flowmol3_materializer()
    native = _make_native(atom_count=15)
    env = m.native_to_envelope(native)
    assert env.observables["atom_count_min"] == 15
    assert env.observables["atom_count_max"] == 15
    back = m.envelope_to_native(env, atom_count=native.atom_count)
    assert back.atom_count == 15
    assert back.backend_kind == "flowmol3"


def test_pair_entropy_from_json_histogram() -> None:
    m = default_flowmol3_materializer()
    native = _make_native(atom_count=10, raw_pair_histogram=[5, 3, 2, 0, 1])
    env = m.native_to_envelope(native)
    assert env.observables["pair_entropy"] > 0.0


def test_valence_hash_stable_across_replays() -> None:
    m1 = default_flowmol3_materializer()
    m2 = default_flowmol3_materializer()
    native = _make_native(atom_count=8)
    env1 = m1.native_to_envelope(native)
    env2 = m2.native_to_envelope(native)
    assert env1.observables["valence_rules_hash"] == env2.observables["valence_rules_hash"]


def test_override_keys_passthrough() -> None:
    m = ConcreteFlowMol3Materializer(
        envelope_observables_override={"coordinate_extent_rms": 2.5, "custom_key": "value"}
    )
    native = _make_native(atom_count=4)
    env = m.native_to_envelope(native)
    assert env.observables["coordinate_extent_rms"] == 2.5
    assert env.observables["custom_key"] == "value"


def test_graph_complexity_max_is_atom_count_squared() -> None:
    m = default_flowmol3_materializer()
    native = _make_native(atom_count=7)
    env = m.native_to_envelope(native)
    assert env.observables["graph_complexity_max"] == 49


def test_loss_tolerance_per_channel() -> None:
    m = default_flowmol3_materializer()
    tol = m.loss_tolerance_by_channel
    assert tol["coordinate"] == 0.0
    assert tol["charge"] == 0.0
    assert tol["raw_pair"] == 1.0
    assert tol["atom_type"] == 1.0


def test_validate_roundtrip_ok() -> None:
    m = default_flowmol3_materializer()
    native = _make_native(atom_count=10)
    ok, errs = m.validate_roundtrip(native)
    assert ok, errs


def test_envelope_keys_match_vocabulary() -> None:
    m = default_flowmol3_materializer()
    native = _make_native(atom_count=5)
    env = m.native_to_envelope(native)
    for key in FLOWMOL3_ENVELOPE_KEYS:
        assert key in env.observables, f"missing envelope key: {key}"


def test_geometry_pass_default_true() -> None:
    m = default_flowmol3_materializer()
    native = _make_native(atom_count=3)
    env = m.native_to_envelope(native)
    assert env.observables["geometry_pass"] is True
    assert env.observables["materialization_pass"] is True
