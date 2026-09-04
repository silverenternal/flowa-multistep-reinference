"""Unit tests for :mod:`adaptive_reflow.core.graph_wrapper`.

Wave 24 MUST-3 partial completion — the framework-core glue
module that wraps graph-shaped payloads (FlowMol3, GraphBFN,
ProtBFN, LineageFlow).

All tests are stdlib + numpy only (CPU-only sandbox). The
DGL/PyG bridge is exercised via the lazy-import probe (which
returns ``None`` when neither backend is installed).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from adaptive_reflow.core.graph_wrapper import (
    DGLGraphBridge,
    DEFAULT_EDGE_FEATURE_DIM,
    DEFAULT_GRAPH_FEATURE_DIM,
    DEFAULT_NODE_FEATURE_DIM,
    EdgeIndexDType,
    GraphBackendProbe,
    GraphBatch,
    GraphPayload,
    blend_graph_features,
    empty_graph_payload,
    merge_graph_batches,
    probe_graph_backends,
    random_graph_payload,
    split_graph_batch,
)


# ---------------------------------------------------------------------------
# Test 1: GraphPayload validation
# ---------------------------------------------------------------------------


def test_graph_payload_shape_validation() -> None:
    """Node features must be 2D ``(N, d_node)``."""
    nf = np.zeros((5, 8), dtype=np.float64)
    ei = np.zeros((2, 6), dtype=np.int64)
    ef = np.zeros((6, 4), dtype=np.float64)
    gf = np.zeros(8, dtype=np.float64)
    payload = GraphPayload(node_features=nf, edge_index=ei, edge_features=ef, graph_features=gf)
    assert payload.num_edges == 6
    assert payload.node_feature_dim == 8
    assert payload.edge_feature_dim == 4
    assert payload.graph_feature_dim == 8
    assert payload.resolved_num_nodes == 5


def test_graph_payload_rejects_1d_node_features() -> None:
    with pytest.raises(ValueError, match=r"\(N, d_node\)"):
        GraphPayload(
            node_features=np.zeros((8,), dtype=np.float64),
            edge_index=np.zeros((2, 0), dtype=np.int64),
            edge_features=np.zeros((0, 4), dtype=np.float64),
            graph_features=np.zeros(8, dtype=np.float64),
        )


def test_graph_payload_rejects_mismatched_edge_count() -> None:
    with pytest.raises(ValueError, match="row count must equal"):
        GraphPayload(
            node_features=np.zeros((5, 8), dtype=np.float64),
            edge_index=np.zeros((2, 6), dtype=np.int64),
            edge_features=np.zeros((3, 4), dtype=np.float64),  # wrong row count
            graph_features=np.zeros(8, dtype=np.float64),
        )


def test_graph_payload_rejects_bad_edge_index_shape() -> None:
    with pytest.raises(ValueError, match=r"\(2, E\)"):
        GraphPayload(
            node_features=np.zeros((5, 8), dtype=np.float64),
            edge_index=np.zeros((3, 6), dtype=np.int64),  # 3 rows, not 2
            edge_features=np.zeros((6, 4), dtype=np.float64),
            graph_features=np.zeros(8, dtype=np.float64),
        )


# ---------------------------------------------------------------------------
# Test 2: digest determinism
# ---------------------------------------------------------------------------


def test_graph_payload_digest_is_byte_stable() -> None:
    payload = random_graph_payload(
        num_nodes=4, num_edges=3,
        node_feature_dim=8, edge_feature_dim=4, graph_feature_dim=6,
        seed=42,
    )
    a = payload.digest()
    b = payload.digest()
    assert a == b
    assert len(a) == 64  # SHA-256 hex


def test_graph_payload_to_dict_carries_summary() -> None:
    payload = random_graph_payload(
        num_nodes=3, num_edges=2,
        node_feature_dim=4, edge_feature_dim=2, graph_feature_dim=6,
        seed=0,
    )
    blob = payload.to_dict()
    assert blob["num_nodes"] == 3
    assert blob["num_edges"] == 2
    assert blob["node_feature_dim"] == 4
    assert blob["edge_feature_dim"] == 2
    assert blob["graph_feature_dim"] == 6
    assert isinstance(blob["node_features_first"], list)
    assert isinstance(blob["graph_features_first"], list)


# ---------------------------------------------------------------------------
# Test 3: convenience constructors
# ---------------------------------------------------------------------------


def test_empty_graph_payload_is_byte_stable() -> None:
    a = empty_graph_payload(seed=7)
    b = empty_graph_payload(seed=7)
    assert a.digest() == b.digest()
    assert a.resolved_num_nodes == 0
    assert a.num_edges == 0


def test_random_graph_payload_uses_seed_deterministically() -> None:
    a = random_graph_payload(num_nodes=8, num_edges=4, seed=42)
    b = random_graph_payload(num_nodes=8, num_edges=4, seed=42)
    assert a.digest() == b.digest()


def test_random_graph_payload_different_seeds_differ() -> None:
    a = random_graph_payload(num_nodes=4, num_edges=2, seed=0)
    b = random_graph_payload(num_nodes=4, num_edges=2, seed=1)
    assert a.digest() != b.digest()


# ---------------------------------------------------------------------------
# Test 4: merge_graph_batches + split_graph_batch
# ---------------------------------------------------------------------------


def test_merge_then_split_round_trip() -> None:
    payloads = [
        random_graph_payload(
            num_nodes=3, num_edges=2,
            node_feature_dim=8, edge_feature_dim=4, graph_feature_dim=6,
            seed=i,
        )
        for i in range(3)
    ]
    batch = merge_graph_batches(payloads)
    assert batch.num_graphs == 3
    assert batch.total_num_nodes == 9
    assert batch.total_num_edges == 6
    # Split should reproduce the originals (within node-index
    # reindexing tolerance — the split subtracts the per-graph
    # node offset so the edge indices are in the per-graph space).
    split = split_graph_batch(batch)
    assert len(split) == 3
    for original, recovered in zip(payloads, split):
        assert original.node_features.shape == recovered.node_features.shape
        np.testing.assert_array_equal(original.node_features, recovered.node_features)
        np.testing.assert_array_equal(original.edge_features, recovered.edge_features)
        np.testing.assert_array_equal(original.graph_features, recovered.graph_features)
        np.testing.assert_array_equal(original.edge_index, recovered.edge_index)


def test_merge_graph_batches_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one payload"):
        merge_graph_batches([])


def test_merge_graph_batches_rejects_dim_mismatch() -> None:
    a = random_graph_payload(num_nodes=2, num_edges=1, node_feature_dim=8, seed=0)
    b = random_graph_payload(num_nodes=2, num_edges=1, node_feature_dim=16, seed=1)
    with pytest.raises(ValueError, match="node_feature_dim mismatch"):
        merge_graph_batches([a, b])


def test_split_then_merge_round_trip() -> None:
    """The batch's ``split`` method equals ``split_graph_batch``."""
    payloads = [
        random_graph_payload(
            num_nodes=2, num_edges=1,
            node_feature_dim=4, edge_feature_dim=2, graph_feature_dim=6,
            seed=i,
        )
        for i in range(2)
    ]
    batch = merge_graph_batches(payloads)
    via_method = batch.split()
    via_fn = split_graph_batch(batch)
    assert len(via_method) == len(via_fn)
    for a, b in zip(via_method, via_fn):
        np.testing.assert_array_equal(a.node_features, b.node_features)
        np.testing.assert_array_equal(a.edge_index, b.edge_index)


def test_batch_total_edges_counts_empty_graphs_correctly() -> None:
    """An empty graph in a batch contributes 0 edges to the totals."""
    empty = empty_graph_payload()
    non_empty = random_graph_payload(num_nodes=4, num_edges=3, seed=0)
    batch = merge_graph_batches([empty, non_empty])
    assert batch.total_num_edges == 3
    assert batch.total_num_nodes == 4
    assert batch.num_graphs == 2


# ---------------------------------------------------------------------------
# Test 5: blend_graph_features
# ---------------------------------------------------------------------------


def test_blend_graph_features_extreme_endpoints() -> None:
    """``m=1.0`` returns the prior; ``m=0.0`` returns the fresh."""
    prior = random_graph_payload(
        num_nodes=4, num_edges=2,
        node_feature_dim=4, edge_feature_dim=2, graph_feature_dim=6,
        seed=10,
    )
    fresh = random_graph_payload(
        num_nodes=4, num_edges=2,
        node_feature_dim=4, edge_feature_dim=2, graph_feature_dim=6,
        seed=99,
    )
    blended_full = blend_graph_features(prior, fresh, 1.0)
    np.testing.assert_array_equal(blended_full.node_features, prior.node_features)
    np.testing.assert_array_equal(blended_full.edge_features, prior.edge_features)
    np.testing.assert_array_equal(blended_full.graph_features, prior.graph_features)

    blended_none = blend_graph_features(prior, fresh, 0.0)
    np.testing.assert_array_equal(blended_none.node_features, fresh.node_features)
    np.testing.assert_array_equal(blended_none.edge_features, fresh.edge_features)
    np.testing.assert_array_equal(blended_none.graph_features, fresh.graph_features)


def test_blend_graph_features_midpoint() -> None:
    """``m=0.5`` returns the arithmetic mean of the two payloads."""
    prior = random_graph_payload(
        num_nodes=3, num_edges=2,
        node_feature_dim=4, edge_feature_dim=2, graph_feature_dim=6,
        seed=1,
    )
    fresh = random_graph_payload(
        num_nodes=3, num_edges=2,
        node_feature_dim=4, edge_feature_dim=2, graph_feature_dim=6,
        seed=2,
    )
    blended = blend_graph_features(prior, fresh, 0.5)
    expected_nodes = 0.5 * prior.node_features + 0.5 * fresh.node_features
    expected_edges = 0.5 * prior.edge_features + 0.5 * fresh.edge_features
    expected_graph = 0.5 * prior.graph_features + 0.5 * fresh.graph_features
    np.testing.assert_allclose(blended.node_features, expected_nodes, atol=1e-12)
    np.testing.assert_allclose(blended.edge_features, expected_edges, atol=1e-12)
    np.testing.assert_allclose(blended.graph_features, expected_graph, atol=1e-12)


def test_blend_graph_features_preserves_edge_topology() -> None:
    """The blended payload's ``edge_index`` is taken from ``prior`` (topology preserved)."""
    prior = random_graph_payload(num_nodes=3, num_edges=2, seed=0)
    fresh = random_graph_payload(num_nodes=3, num_edges=2, seed=1)
    blended = blend_graph_features(prior, fresh, 0.3)
    np.testing.assert_array_equal(blended.edge_index, prior.edge_index)


def test_blend_graph_features_clamps_memory_fraction() -> None:
    """``memory_fraction`` is clamped to ``[0, 1]``."""
    prior = random_graph_payload(num_nodes=3, num_edges=2, seed=0)
    fresh = random_graph_payload(num_nodes=3, num_edges=2, seed=1)
    blended = blend_graph_features(prior, fresh, 5.0)  # clamps to 1.0
    np.testing.assert_array_equal(blended.node_features, prior.node_features)


def test_blend_graph_features_rejects_shape_mismatch() -> None:
    """Mismatched node / edge / graph shapes raise ``ValueError``."""
    prior = random_graph_payload(num_nodes=3, num_edges=2, node_feature_dim=4, seed=0)
    fresh = random_graph_payload(num_nodes=3, num_edges=2, node_feature_dim=8, seed=1)
    with pytest.raises(ValueError, match="node_features shape mismatch"):
        blend_graph_features(prior, fresh, 0.5)


# ---------------------------------------------------------------------------
# Test 6: backend probe + bridge (lazy-import behaviour)
# ---------------------------------------------------------------------------


def test_probe_graph_backends_returns_valid_probe() -> None:
    probe = probe_graph_backends()
    assert isinstance(probe, GraphBackendProbe)
    assert probe.preferred in ("dgl", "pyg", "numpy")
    assert isinstance(probe.has_dgl, bool)
    assert isinstance(probe.has_pyg, bool)
    # numpy is always "available" in the framework's NumPy fallback.
    assert probe.preferred == "numpy" or probe.has_dgl or probe.has_pyg


def test_bridge_to_dgl_returns_none_when_dgl_absent() -> None:
    """When DGL is unavailable, ``to_dgl`` returns ``None`` (no crash)."""
    probe = GraphBackendProbe(has_dgl=False, has_pyg=False, preferred="numpy")
    bridge = DGLGraphBridge(probe=probe)
    payload = random_graph_payload(num_nodes=3, num_edges=2, seed=0)
    assert bridge.to_dgl(payload) is None


def test_bridge_to_pyg_returns_none_when_pyg_absent() -> None:
    probe = GraphBackendProbe(has_dgl=False, has_pyg=False, preferred="numpy")
    bridge = DGLGraphBridge(probe=probe)
    payload = random_graph_payload(num_nodes=3, num_edges=2, seed=0)
    assert bridge.to_pyg(payload) is None


def test_bridge_probe_property_matches_constructor() -> None:
    probe = GraphBackendProbe(has_dgl=False, has_pyg=True, preferred="pyg")
    bridge = DGLGraphBridge(probe=probe)
    assert bridge.probe.has_pyg is True
    assert bridge.probe.preferred == "pyg"


# ---------------------------------------------------------------------------
# Test 7: constants exposed at the package surface
# ---------------------------------------------------------------------------


def test_default_dims_exposed() -> None:
    """The default dimension constants match the canonical FlowMol3/GraphBFN shapes."""
    assert DEFAULT_NODE_FEATURE_DIM == 64
    assert DEFAULT_EDGE_FEATURE_DIM == 16
    assert DEFAULT_GRAPH_FEATURE_DIM == 32
    assert EdgeIndexDType == np.int64
