"""DGL-style graph wrapper — framework-core glue for graph-based models.

Purpose
-------

PHASE-3 glue extraction (``todo/PHASE-3-glue-layer-improvement.md`` §
"Example glue patterns"): centralise the **DGL / PyG-style graph
payload** wrapper that every graph-based adapter
(:mod:`adaptive_reflow.adapters.flowmol3`,
:mod:`adaptive_reflow.adapters.graphbfn`,
:mod:`adaptive_reflow.adapters.protbfn_abbfn_adapter`,
:mod:`adaptive_reflow.adapters.lineageflow`,
…) was previously re-typing. The wrapper exposes:

* :class:`GraphPayload` — graph-shaped payload with separate
  ``node_features``, ``edge_index``, ``edge_features``,
  ``graph_features`` arrays. Mirrors the per-adapter
  graph-shaped tensor dict (the adapters pass these through the
  framework's ``TensorRef``-tagged opaque channels rather than
  the public Protocol surface — see ``GraphBFNAdapter`` §
  "Graph-shaped payloads" for the rationale).
* :class:`GraphBatch` — batched graph container with
  ``batch_offsets`` (the CSR-style row-pointer offsets that
  PyG / DGL use to split a batched node tensor back into
  per-graph node tensors).
* :func:`merge_graph_batches` / :func:`split_graph_batch` —
  pure numpy merge + split. No torch / DGL / PyG dependency at
  module level; lazy import only inside the graph-runtime
  bridge functions.
* :func:`blend_graph_features` — restart-blend helper that
  applies the ``m * prior + (1 - m) * fresh`` blend to the
  graph-shaped tensors of a :class:`GraphPayload`. Mirrors the
  per-adapter ``_blend_graph_param`` helpers.
* :class:`DGLGraphBridge` — adapter-side helper that converts a
  :class:`GraphPayload` into a DGL ``DGLGraph`` (when DGL is
  importable) or a PyG ``Data`` object (when PyG is importable)
  for the upstream forward call. The bridge is **lazy-import**
  so the framework never requires DGL / PyG at import time.

Constraints
-----------

* Stdlib + numpy only at module level. ``torch`` / ``dgl`` /
  ``torch_geometric`` are imported lazily inside the bridge
  functions that need them so the framework never requires
  them at import time.
* All graph shapes are explicit; the wrapper does not
  auto-infer dimensions from the upstream convention (each
  adapter overrides the dimension constants).
* Deterministic for fixed inputs: ``merge_graph_batches``
  preserves node / edge ordering across calls.

Channel-domain note
-------------------

The framework's :data:`ChannelDomain` literal includes
``"graph"`` (see :mod:`adaptive_reflow.universal.adapter`),
which the per-adapter ``channel_domains`` mapping declares for
graph-shaped channels (e.g. ``ChannelName("atom_features"):
"graph"``). The wrapper does not enforce the channel-domain
typing itself — that is the adapter's responsibility — but the
shape semantics (``node_features`` of shape ``(N, d_node)``,
``edge_index`` of shape ``(2, E)``) match what the protocol
boundary expects.
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

ArrayF64 = NDArray[np.float64]

#: Edge-index dtype. ``int64`` matches both DGL and PyG.
EdgeIndexDType = np.int64

#: Default node-feature dim (atomic-feature dimension used by
#: FlowMol3 / ProtBFN / LineageFlow / GraphBFN).
DEFAULT_NODE_FEATURE_DIM: int = 64

#: Default edge-feature dim (bond-feature dimension).
DEFAULT_EDGE_FEATURE_DIM: int = 16

#: Default graph-feature dim (global-graph feature dim).
DEFAULT_GRAPH_FEATURE_DIM: int = 32


@dataclass(frozen=True)
class GraphPayload:
    """Graph-shaped payload for the framework's opaque graph channels.

    Attributes
    ----------
    node_features:
        Per-node feature tensor of shape ``(N, d_node)``.
    edge_index:
        Edge-index tensor of shape ``(2, E)`` — the COO sparse
        format used by both DGL and PyG (``edge_index[0]`` is
        the source-node array, ``edge_index[1]`` the
        destination-node array).
    edge_features:
        Per-edge feature tensor of shape ``(E, d_edge)``.
        May be empty (``shape=(0, d_edge)``) when the graph is
        edgeless.
    graph_features:
        Per-graph feature tensor of shape ``(d_graph,)``.
        Optional — pass an empty array when the graph has no
        global features.
    num_nodes:
        Explicit node count. Defaults to ``node_features.shape[0]``
        when ``None``. Useful when ``node_features`` is empty
        (e.g. an empty graph placeholder).
    """

    node_features: ArrayF64
    edge_index: NDArray[np.int64]
    edge_features: ArrayF64
    graph_features: ArrayF64
    num_nodes: int | None = None

    def __post_init__(self) -> None:
        nf = np.asarray(self.node_features, dtype=np.float64)
        if nf.ndim != 2:
            raise ValueError(
                f"node_features must be (N, d_node); got shape {tuple(nf.shape)!r}"
            )
        ei = np.asarray(self.edge_index, dtype=EdgeIndexDType)
        if ei.ndim != 2 or ei.shape[0] != 2:
            raise ValueError(
                f"edge_index must be (2, E); got shape {tuple(ei.shape)!r}"
            )
        ef = np.asarray(self.edge_features, dtype=np.float64)
        if ef.ndim != 2:
            raise ValueError(
                f"edge_features must be (E, d_edge); got shape {tuple(ef.shape)!r}"
            )
        if ef.shape[0] != int(ei.shape[1]):
            raise ValueError(
                "edge_features row count must equal edge_index column count"
                f" ({int(ei.shape[1])}); got {int(ef.shape[0])}"
            )
        gf = np.asarray(self.graph_features, dtype=np.float64)
        if gf.ndim != 1:
            raise ValueError(
                f"graph_features must be (d_graph,); got shape {tuple(gf.shape)!r}"
            )

    @property
    def num_edges(self) -> int:
        return int(self.edge_index.shape[1])

    @property
    def node_feature_dim(self) -> int:
        return int(self.node_features.shape[1])

    @property
    def edge_feature_dim(self) -> int:
        return int(self.edge_features.shape[1])

    @property
    def graph_feature_dim(self) -> int:
        return int(self.graph_features.shape[0])

    @property
    def resolved_num_nodes(self) -> int:
        return int(self.num_nodes) if self.num_nodes is not None else int(
            self.node_features.shape[0]
        )

    def digest(self) -> str:
        """SHA-256 hex digest of the payload's byte content.

        Used by the per-adapter ``digest_state`` machinery so
        the restart-blend logic can dedupe graph payloads across
        rounds without re-traversing the COO edge list.
        """
        blob = (
            np.ascontiguousarray(self.node_features).tobytes()
            + np.ascontiguousarray(self.edge_index).tobytes()
            + np.ascontiguousarray(self.edge_features).tobytes()
            + np.ascontiguousarray(self.graph_features).tobytes()
        )
        return hashlib.sha256(blob).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe summary dict (for audit logging)."""
        return {
            "num_nodes": int(self.resolved_num_nodes),
            "num_edges": int(self.num_edges),
            "node_feature_dim": int(self.node_feature_dim),
            "edge_feature_dim": int(self.edge_feature_dim),
            "graph_feature_dim": int(self.graph_feature_dim),
            "node_features_first": [
                float(self.node_features[0, i]) if self.node_features.size else 0.0
                for i in range(min(3, self.node_feature_dim))
            ],
            "graph_features_first": [
                float(self.graph_features[i])
                for i in range(min(3, self.graph_feature_dim))
            ],
            "digest": str(self.digest()),
        }


# ---------------------------------------------------------------------------
# Graph-batch merge / split
# ---------------------------------------------------------------------------


@dataclass
class GraphBatch:
    """Batched graph container.

    Stores a concatenation of per-graph :class:`GraphPayload` along
    the node axis (with edge indices reindexed by the per-graph
    offset). ``batch_offsets`` is the CSR-style row-pointer
    offsets used to split the batched node tensor back into
    per-graph node tensors (``batch_offsets[i]:batch_offsets[i+1]``
    is the node range for graph ``i``).

    Attributes
    ----------
    node_features:
        Batched node features of shape ``(sum_N, d_node)``.
    edge_index:
        Batched edge indices of shape ``(2, sum_E)`` (reindexed).
    edge_features:
        Batched edge features of shape ``(sum_E, d_edge)``.
    graph_features:
        Batched graph features of shape ``(B, d_graph)``.
    batch_offsets:
        Per-graph node offsets, shape ``(B + 1,)``. ``offsets[0]
        = 0`` and ``offsets[-1] = sum_N``.
    edge_offsets:
        Per-graph edge offsets, shape ``(B + 1,)`` (same CSR
        semantics as ``batch_offsets``).
    """

    node_features: ArrayF64
    edge_index: NDArray[np.int64]
    edge_features: ArrayF64
    graph_features: ArrayF64
    batch_offsets: NDArray[np.int64]
    edge_offsets: NDArray[np.int64]

    @property
    def num_graphs(self) -> int:
        return int(self.batch_offsets.shape[0]) - 1

    @property
    def total_num_nodes(self) -> int:
        return int(self.node_features.shape[0])

    @property
    def total_num_edges(self) -> int:
        return int(self.edge_index.shape[1])

    def split(self) -> list[GraphPayload]:
        """Inverse of :func:`merge_graph_batches`.

        Returns the per-graph :class:`GraphPayload` list.
        """
        return split_graph_batch(self)


def merge_graph_batches(payloads: Iterable[GraphPayload]) -> GraphBatch:
    """Concatenate a sequence of :class:`GraphPayload` into a :class:`GraphBatch`.

    Reindexes the per-graph ``edge_index`` by the cumulative
    node offset (matches DGL's ``batch`` op and PyG's
    ``Batch.from_data_list`` semantics).
    """
    plist = list(payloads)
    if not plist:
        raise ValueError("merge_graph_batches requires at least one payload")

    d_node = plist[0].node_feature_dim
    d_edge = plist[0].edge_feature_dim
    d_graph = plist[0].graph_feature_dim

    node_chunks: list[ArrayF64] = []
    edge_chunks: list[ArrayF64] = []
    edge_idx_chunks: list[NDArray[np.int64]] = []
    edge_feat_chunks: list[ArrayF64] = []
    graph_chunks: list[ArrayF64] = []
    node_offsets: list[int] = [0]
    edge_offsets: list[int] = [0]

    node_cursor = 0
    edge_cursor = 0
    for p in plist:
        if p.node_feature_dim != d_node:
            raise ValueError("node_feature_dim mismatch in merge_graph_batches")
        if p.edge_feature_dim != d_edge:
            raise ValueError("edge_feature_dim mismatch in merge_graph_batches")
        if p.graph_feature_dim != d_graph:
            raise ValueError("graph_feature_dim mismatch in merge_graph_batches")
        node_chunks.append(np.asarray(p.node_features, dtype=np.float64))
        if p.edge_index.size:
            edge_idx_chunks.append(
                np.asarray(p.edge_index, dtype=EdgeIndexDType) + node_cursor
            )
            edge_feat_chunks.append(np.asarray(p.edge_features, dtype=np.float64))
            edge_cursor += int(p.edge_index.shape[1])
        graph_chunks.append(np.asarray(p.graph_features, dtype=np.float64))
        node_cursor += int(p.resolved_num_nodes)
        node_offsets.append(node_cursor)
        edge_offsets.append(edge_cursor)

    node_features = (
        np.concatenate(node_chunks, axis=0).reshape(-1, d_node)
        if len(node_chunks) > 1
        else np.asarray(node_chunks[0], dtype=np.float64).reshape(-1, d_node)
    )
    edge_index = (
        np.concatenate(edge_idx_chunks, axis=1).reshape(2, -1)
        if edge_idx_chunks
        else np.zeros((2, 0), dtype=EdgeIndexDType)
    )
    edge_features = (
        np.concatenate(edge_feat_chunks, axis=0).reshape(-1, d_edge)
        if edge_feat_chunks
        else np.zeros((0, d_edge), dtype=np.float64)
    )
    graph_features = (
        np.stack(graph_chunks, axis=0).reshape(-1, d_graph)
        if len(graph_chunks) > 1
        else np.asarray(graph_chunks[0], dtype=np.float64).reshape(1, d_graph)
    )
    return GraphBatch(
        node_features=node_features,
        edge_index=edge_index,
        edge_features=edge_features,
        graph_features=graph_features,
        batch_offsets=np.asarray(node_offsets, dtype=EdgeIndexDType),
        edge_offsets=np.asarray(edge_offsets, dtype=EdgeIndexDType),
    )


def split_graph_batch(batch: GraphBatch) -> list[GraphPayload]:
    """Split a :class:`GraphBatch` into the per-graph :class:`GraphPayload` list."""
    out: list[GraphPayload] = []
    for i in range(batch.num_graphs):
        n_start = int(batch.batch_offsets[i])
        n_end = int(batch.batch_offsets[i + 1])
        e_start = int(batch.edge_offsets[i])
        e_end = int(batch.edge_offsets[i + 1])
        nf = batch.node_features[n_start:n_end]
        # Undo the node-cursor reindexing.
        ei = batch.edge_index[:, e_start:e_end] - n_start
        ef = batch.edge_features[e_start:e_end]
        gf = batch.graph_features[i]
        out.append(
            GraphPayload(
                node_features=np.asarray(nf, dtype=np.float64),
                edge_index=np.asarray(ei, dtype=EdgeIndexDType),
                edge_features=np.asarray(ef, dtype=np.float64),
                graph_features=np.asarray(gf, dtype=np.float64),
                num_nodes=int(n_end - n_start),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Graph-blend (restart blend for graph-shaped channels)
# ---------------------------------------------------------------------------


def blend_graph_features(
    prior: GraphPayload,
    fresh: GraphPayload,
    memory_fraction: float,
) -> GraphPayload:
    """Restart-blend helper for graph-shaped payloads.

    Computes
    ``blended_X = m * prior_X + (1 - m) * fresh_X`` for the
    node / edge / graph feature tensors, where
    ``m = clamp(memory_fraction, 0, 1)``. Edge indices are
    taken from ``prior`` (the restart boundary preserves the
    graph topology across rounds). ``prior`` and ``fresh`` must
    have the same shape on every channel; mismatches raise
    :class:`ValueError`.
    """
    m = max(0.0, min(1.0, float(memory_fraction)))
    if prior.node_features.shape != fresh.node_features.shape:
        raise ValueError("node_features shape mismatch in blend_graph_features")
    if prior.edge_features.shape != fresh.edge_features.shape:
        raise ValueError("edge_features shape mismatch in blend_graph_features")
    if prior.graph_features.shape != fresh.graph_features.shape:
        raise ValueError("graph_features shape mismatch in blend_graph_features")
    blended_nodes = (m * prior.node_features + (1.0 - m) * fresh.node_features).astype(
        np.float64
    )
    blended_edges = (m * prior.edge_features + (1.0 - m) * fresh.edge_features).astype(
        np.float64
    )
    blended_graph = (
        m * prior.graph_features + (1.0 - m) * fresh.graph_features
    ).astype(np.float64)
    return GraphPayload(
        node_features=blended_nodes,
        edge_index=np.asarray(prior.edge_index, dtype=EdgeIndexDType),
        edge_features=blended_edges,
        graph_features=blended_graph,
        num_nodes=int(prior.resolved_num_nodes),
    )


# ---------------------------------------------------------------------------
# DGL / PyG bridge (lazy imports)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphBackendProbe:
    """Snapshot of the available graph-runtime backends.

    The probe is a tiny contract — the per-adapter code reads
    ``probe.has_dgl`` / ``probe.has_pyg`` and dispatches into
    the corresponding branch. The probe is computed lazily so
    the import-time graph-runtime detection doesn't pay the
    cost of importing both DGL and PyG.
    """

    has_dgl: bool
    has_pyg: bool
    preferred: str  # ``"dgl"`` / ``"pyg"`` / ``"numpy"``

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_dgl": bool(self.has_dgl),
            "has_pyg": bool(self.has_pyg),
            "preferred": str(self.preferred),
        }


def probe_graph_backends() -> GraphBackendProbe:
    """Detect which graph runtime (DGL / PyG / numpy-only) is available."""
    import importlib.util as _il

    has_dgl = _il.find_spec("dgl") is not None
    has_pyg = _il.find_spec("torch_geometric") is not None
    if has_dgl:
        preferred = "dgl"
    elif has_pyg:
        preferred = "pyg"
    else:
        preferred = "numpy"
    return GraphBackendProbe(
        has_dgl=bool(has_dgl),
        has_pyg=bool(has_pyg),
        preferred=str(preferred),
    )


class DGLGraphBridge:
    """Lazy bridge between :class:`GraphPayload` and DGL / PyG objects.

    The bridge exposes two methods:

    * :meth:`to_dgl` — returns a ``dgl.DGLGraph`` (when DGL is
      importable) with ``ndata["h"]`` / ``edata["h"]`` /
      ``gdata["h"]`` populated from the :class:`GraphPayload`.
      Returns ``None`` when DGL is unavailable.
    * :meth:`to_pyg` — returns a ``torch_geometric.data.Data``
      (when PyG is importable) with ``x`` / ``edge_index`` /
      ``edge_attr`` populated. Returns ``None`` when PyG is
      unavailable.
    * :meth:`from_dgl` / :meth:`from_pyg` — inverse bridges that
      build a :class:`GraphPayload` from the upstream object.

    The bridge is **never import-fatal**: when neither backend
    is available both methods return ``None`` and the adapter
    falls back to its synthetic-mode NumPy shim.
    """

    __slots__ = ("_probe",)

    def __init__(self, probe: GraphBackendProbe | None = None) -> None:
        self._probe: GraphBackendProbe = probe or probe_graph_backends()

    @property
    def probe(self) -> GraphBackendProbe:
        return self._probe

    def to_dgl(self, payload: GraphPayload) -> Any | None:
        """Return a DGL graph for ``payload``, or ``None`` when DGL is absent."""
        if not self._probe.has_dgl:
            return None
        try:
            import dgl  # local import — DGL is optional.
            import torch  # local import.
        except ImportError:
            return None
        g = dgl.graph(
            (
                np.ascontiguousarray(payload.edge_index[0], dtype=np.int64),
                np.ascontiguousarray(payload.edge_index[1], dtype=np.int64),
            ),
            num_nodes=int(payload.resolved_num_nodes),
        )
        g.ndata["h"] = torch.as_tensor(
            np.ascontiguousarray(payload.node_features, dtype=np.float64),
            dtype=torch.float32,
        )
        if payload.num_edges > 0:
            g.edata["h"] = torch.as_tensor(
                np.ascontiguousarray(payload.edge_features, dtype=np.float64),
                dtype=torch.float32,
            )
        if payload.graph_features.size:
            g.gdata = {"h": torch.as_tensor(
                np.ascontiguousarray(payload.graph_features, dtype=np.float64),
                dtype=torch.float32,
            )}
        return g

    def to_pyg(self, payload: GraphPayload) -> Any | None:
        """Return a PyG Data object for ``payload``, or ``None`` when PyG is absent."""
        if not self._probe.has_pyg:
            return None
        try:
            from torch_geometric.data import Data  # local import.
            import torch  # local import.
        except ImportError:
            return None
        data = Data(
            x=torch.as_tensor(
                np.ascontiguousarray(payload.node_features, dtype=np.float64),
                dtype=torch.float32,
            ),
            edge_index=torch.as_tensor(
                np.ascontiguousarray(payload.edge_index, dtype=np.int64),
                dtype=torch.long,
            ),
        )
        if payload.num_edges > 0:
            data.edge_attr = torch.as_tensor(
                np.ascontiguousarray(payload.edge_features, dtype=np.float64),
                dtype=torch.float32,
            )
        if payload.graph_features.size:
            data.graph_attr = torch.as_tensor(
                np.ascontiguousarray(payload.graph_features, dtype=np.float64),
                dtype=torch.float32,
            )
        return data

    def from_dgl(self, graph: Any) -> GraphPayload:
        """Build a :class:`GraphPayload` from a DGL graph."""
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError("from_dgl requires torch") from exc

        nf = graph.ndata["h"].detach().cpu().numpy() if "h" in graph.ndata else np.zeros(
            (int(graph.num_nodes()), DEFAULT_NODE_FEATURE_DIM), dtype=np.float64
        )
        ei = (
            torch.stack(graph.edges()).detach().cpu().numpy().astype(np.int64)
            if int(graph.num_edges()) > 0
            else np.zeros((2, 0), dtype=np.int64)
        )
        ef = (
            graph.edata["h"].detach().cpu().numpy()
            if "h" in graph.edata and int(graph.num_edges()) > 0
            else np.zeros((0, DEFAULT_EDGE_FEATURE_DIM), dtype=np.float64)
        )
        gf = (
            graph.gdata["h"].detach().cpu().numpy()
            if hasattr(graph, "gdata") and "h" in graph.gdata
            else np.zeros(DEFAULT_GRAPH_FEATURE_DIM, dtype=np.float64)
        )
        return GraphPayload(
            node_features=np.asarray(nf, dtype=np.float64),
            edge_index=ei,
            edge_features=ef,
            graph_features=gf,
            num_nodes=int(graph.num_nodes()),
        )

    def from_pyg(self, data: Any) -> GraphPayload:
        """Build a :class:`GraphPayload` from a PyG Data object."""
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError("from_pyg requires torch") from exc

        nf = (
            data.x.detach().cpu().numpy()
            if getattr(data, "x", None) is not None
            else np.zeros((0, DEFAULT_NODE_FEATURE_DIM), dtype=np.float64)
        )
        ei = (
            data.edge_index.detach().cpu().numpy().astype(np.int64)
            if getattr(data, "edge_index", None) is not None
            else np.zeros((2, 0), dtype=np.int64)
        )
        ef = (
            data.edge_attr.detach().cpu().numpy()
            if getattr(data, "edge_attr", None) is not None
            else np.zeros((0, DEFAULT_EDGE_FEATURE_DIM), dtype=np.float64)
        )
        gf = (
            data.graph_attr.detach().cpu().numpy()
            if getattr(data, "graph_attr", None) is not None
            else np.zeros(DEFAULT_GRAPH_FEATURE_DIM, dtype=np.float64)
        )
        return GraphPayload(
            node_features=np.asarray(nf, dtype=np.float64),
            edge_index=ei,
            edge_features=ef,
            graph_features=gf,
            num_nodes=int(nf.shape[0]),
        )


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def empty_graph_payload(
    *,
    node_feature_dim: int = DEFAULT_NODE_FEATURE_DIM,
    edge_feature_dim: int = DEFAULT_EDGE_FEATURE_DIM,
    graph_feature_dim: int = DEFAULT_GRAPH_FEATURE_DIM,
    seed: int = 0,
) -> GraphPayload:
    """Build a deterministic empty-graph :class:`GraphPayload`.

    The node / edge / graph features are sampled from
    ``N(0, I)`` via a ``default_rng(seed)`` so two calls with
    the same seed produce byte-identical payloads.
    """
    rng = np.random.default_rng(int(seed))
    return GraphPayload(
        node_features=np.zeros((0, int(node_feature_dim)), dtype=np.float64),
        edge_index=np.zeros((2, 0), dtype=EdgeIndexDType),
        edge_features=np.zeros((0, int(edge_feature_dim)), dtype=np.float64),
        graph_features=rng.standard_normal(int(graph_feature_dim)).astype(np.float64),
        num_nodes=0,
    )


def random_graph_payload(
    *,
    num_nodes: int,
    num_edges: int,
    node_feature_dim: int = DEFAULT_NODE_FEATURE_DIM,
    edge_feature_dim: int = DEFAULT_EDGE_FEATURE_DIM,
    graph_feature_dim: int = DEFAULT_GRAPH_FEATURE_DIM,
    seed: int = 0,
) -> GraphPayload:
    """Build a deterministic random-graph :class:`GraphPayload`.

    The graph topology is sampled uniformly: each edge is a
    random pair ``(u, v)`` from ``[0, num_nodes)``. The node /
    edge / graph features are sampled from ``N(0, I)`` via
    ``default_rng(seed + 1)`` so the seed encodes both topology
    and feature draws deterministically.
    """
    n = int(num_nodes)
    e = int(num_edges)
    rng_topo = np.random.default_rng(int(seed))
    rng_feat = np.random.default_rng(int(seed) + 1)
    if e > 0 and n > 0:
        src = rng_topo.integers(0, n, size=e).astype(EdgeIndexDType)
        dst = rng_topo.integers(0, n, size=e).astype(EdgeIndexDType)
        edge_index = np.stack([src, dst], axis=0)
    else:
        edge_index = np.zeros((2, 0), dtype=EdgeIndexDType)
    node_features = (
        rng_feat.standard_normal((n, int(node_feature_dim))).astype(np.float64)
        if n > 0
        else np.zeros((0, int(node_feature_dim)), dtype=np.float64)
    )
    edge_features = (
        rng_feat.standard_normal((e, int(edge_feature_dim))).astype(np.float64)
        if e > 0
        else np.zeros((0, int(edge_feature_dim)), dtype=np.float64)
    )
    graph_features = rng_feat.standard_normal(int(graph_feature_dim)).astype(np.float64)
    return GraphPayload(
        node_features=node_features,
        edge_index=edge_index,
        edge_features=edge_features,
        graph_features=graph_features,
        num_nodes=int(n),
    )


__all__ = [
    "DEFAULT_EDGE_FEATURE_DIM",
    "DEFAULT_GRAPH_FEATURE_DIM",
    "DEFAULT_NODE_FEATURE_DIM",
    "DGLGraphBridge",
    "EdgeIndexDType",
    "GraphBackendProbe",
    "GraphBatch",
    "GraphPayload",
    "blend_graph_features",
    "empty_graph_payload",
    "merge_graph_batches",
    "probe_graph_backends",
    "random_graph_payload",
    "split_graph_batch",
]
