"""Pytest suite for :class:`ConcreteGraphBFNMaterializer` (D2 — GraphBFN roundtrip)."""

from __future__ import annotations

import json

import pytest

from adaptive_reflow.molecular.materializer import (
    GRAPHBFN_ENVELOPE_KEYS,
    ConcreteGraphBFNMaterializer,
    default_graphbfn_materializer,
)
from adaptive_reflow.universal.materialization import (
    NativeStateBundle,
)


def _make_native(
    node_count: int,
    *,
    edge_count: int | None = None,
    adjacency_histogram: list[int] | None = None,
    source_round: int = 1,
    source_digest: str = "d-graphbfn",
) -> NativeStateBundle:
    channels: dict[str, str] = {
        "nodes": f"graphbfn:nodes:abc:{node_count}",
        "edges": (
            str(edge_count)
            if edge_count is not None
            else f"graphbfn:edges:abc:{node_count * node_count}"
        ),
        "adjacency": (
            json.dumps(adjacency_histogram)
            if adjacency_histogram is not None
            else "graphbfn:adj:abc"
        ),
    }
    return NativeStateBundle(
        channels=channels,
        atom_count=node_count,
        backend_kind="graphbfn",
        source_round=source_round,
        source_digest=source_digest,
    )


def test_node_count_round_trips() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=12)
    env = m.native_to_envelope(native)
    assert env.observables["node_count_min"] == 12
    assert env.observables["node_count_max"] == 12
    back = m.envelope_to_native(env, atom_count=native.atom_count)
    assert back.atom_count == 12
    assert back.backend_kind == "graphbfn"


def test_edge_count_from_channel_payload() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=5, edge_count=12)
    env = m.native_to_envelope(native)
    assert env.observables["edge_count_max"] == 12


def test_edge_count_falls_back_to_node_squared() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=4, edge_count=None)
    env = m.native_to_envelope(native)
    assert env.observables["edge_count_max"] == 16


def test_pair_entropy_from_json_histogram() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=5, adjacency_histogram=[2, 1, 0, 3])
    env = m.native_to_envelope(native)
    assert env.observables["pair_entropy"] > 0.0


def test_graph_complexity_is_node_squared() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=7)
    env = m.native_to_envelope(native)
    assert env.observables["graph_complexity_max"] == 49


def test_valence_hash_stable() -> None:
    m1 = default_graphbfn_materializer()
    m2 = default_graphbfn_materializer()
    native = _make_native(node_count=6, edge_count=10)
    env1 = m1.native_to_envelope(native)
    env2 = m2.native_to_envelope(native)
    assert env1.observables["valence_rules_hash"] == env2.observables["valence_rules_hash"]


def test_roundtrip_ok() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=8)
    ok, errs = m.validate_roundtrip(native)
    assert ok, errs


def test_loss_tolerance_per_channel() -> None:
    m = default_graphbfn_materializer()
    tol = m.loss_tolerance_by_channel
    assert tol["nodes"] == 0.0
    assert tol["edges"] == 1.0
    assert tol["adjacency"] == 1.0


def test_envelope_keys_match_vocabulary() -> None:
    m = default_graphbfn_materializer()
    native = _make_native(node_count=3)
    env = m.native_to_envelope(native)
    for key in GRAPHBFN_ENVELOPE_KEYS:
        assert key in env.observables, f"missing envelope key: {key}"
