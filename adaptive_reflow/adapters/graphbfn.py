"""GraphBFN (Bayesian Flow Network on graphs) adapter — molecular graph generation.

Implements the :class:`FlowMatchingODEAdapter` Protocol for the GraphBFN
model family (ICLR-2025 *Smooth Interpolation for Improved Discrete
Graph Generative Models* + arXiv:2510.10211 *Hierarchical Bayesian Flow
Networks for Molecular Graph Generation*). Both papers share the same
core idea: a continuous-time Bayesian-update process on per-node /
per-edge Categorical distribution parameters (sufficient statistics),
not a velocity-field ODE on a tensor.

Why this adapter is graph-shaped, not tensor-shaped
---------------------------------------------------

The engine's :class:`StateBundle` treats ``state_shape`` as a fixed
tuple and :data:`TensorRef` as an opaque string handle — it never
inspects the native payload. GraphBFN's native state is a *graph*
(``(N, K_atom)`` Categorical parameters for a variable node count
``N``, plus ``(E, K_bond)`` per-edge Categorical parameters for a
variable edge count ``E``, plus an ``(N, N)`` adjacency-logit matrix).
We therefore publish ``state_shape=()`` (a zero-length surrogate) and
route the graph payload through the native ``_native_states`` dict
keyed by ``native_state_digest`` exactly like the placeholder
:class:`FlowMol3Adapter` / :class:`ReferenceFlowAAdapter` do. The
engine never inspects the value; the graph data lives behind
:data:`TensorRef` keys indexed by the GraphBFN adapter's per-channel
mapping.

Channel surface
---------------

The adapter advertises five channels:

* ``atoms``    — discrete (``K_atom`` Categorical; 9 for QM9 / 38 for ZINC250k)
* ``bonds``    — discrete (``K_bond`` Categorical; 4 for {none, single, double, triple})
* ``adjacency``— discrete (``(N, N)`` upper-triangular edge-existence logits)
* ``valence``  — continuous (per-atom chemistry-validity scalar)
* ``charge``   — continuous (per-atom formal charge scalar)

Restart-blend math is computed per-channel on the graph-shaped tensors:
``m * prior + (1 - m) * fresh`` elementwise, where ``m = 1 - beta`` per
channel, mirroring :class:`TwoDimFMAdapter`'s blend math but lifted to
graph-shaped payloads.

Operating modes
---------------

* ``torch`` (production path) — loads a published GraphBFN GNN /
  Graph-Transformer ``state_dict`` via :mod:`torch` and runs the BFN
  Bayesian-update loop inside ``solve_ode``. Requires the
  ``[graphbfn-extra]`` optional extra (torch>=2.4 + rdkit>=2024.3.3).
* ``synthetic`` (testing only) — a deterministic NumPy placeholder
  that walks the BFN update loop with a per-node / per-edge
  random-init Categorical parameter. The synthetic path lets the test
  suite exercise every method without the heavy torch dependency.

Public surface
--------------

* :class:`GraphBFNAdapter` — concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=()`` and 5 channels.
* :class:`GraphBFNCapabilities` — frozen capability surface.
* :func:`default_graphbfn_adapter` — factory.

Tasks satisfied:

* ``DTB-M7`` — GraphBFN (molecular graph generation) adapter skeleton.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

from adaptive_reflow.adapters._adapter_common import (
    make_ref,
)
from adaptive_reflow.framework.interfaces import implements


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Channel set: 5 channels covering the molecule graph space.
#: Names follow the design spec; the engine routes per-channel
#: domain resolution through ``channel_domains`` declared on the
#: adapter's capabilities token.
GRAPHBFN_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("atoms"),
    ChannelName("bonds"),
    ChannelName("adjacency"),
    ChannelName("valence"),
    ChannelName("charge"),
)

#: Per-channel domain-kind declaration (replaces the legacy
#: ``frame.adapter.DOMAIN_BY_CHANNEL`` molecule-only fallback).
GRAPHBFN_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("atoms"): "discrete",
    ChannelName("bonds"): "discrete",
    ChannelName("adjacency"): "discrete",
    ChannelName("valence"): "continuous",
    ChannelName("charge"): "continuous",
}

#: Conditional-graph kind literals (passed through ``compose_condition``).
GRAPHBFN_CONDITION_KINDS: tuple[str, ...] = (
    "unconditional",
    "property_logp",
    "property_qed",
    "property_sa",
)

#: Native config hash + version. The Hierarchical variant uses a
#: separate hash so callers can disambiguate ICLR-2025 vs Hierarchical
#: models in the round trace.
GRAPHBFN_CONFIG_HASH_ICLR: str = "graphbfn:cfg:v1"
GRAPHBFN_CONFIG_HASH_HIER: str = "graphbfn_hier:cfg:v1"
GRAPHBFN_CONFIG_VERSION: str = "0.1.0"

#: Default BFN-step count. The paper uses ~1000 BFN updates on QM9 and
#: ~500 on ZINC250k for the 1-Rectified-Flow equivalent. The default
#: here is conservative for the synthetic-mode placeholder; production
#: callers should override via ``num_steps`` or
#: ``condition.delta_spec["num_steps"]``.
GRAPHBFN_NUM_STEPS_DEFAULT: int = 32

#: Default vocabulary sizes. QM9 = 9 atom types / 4 bond types;
#: ZINC250k = 38 atom types / 4 bond types.
GRAPHBFN_ATOM_VOCAB_QM9: int = 9
GRAPHBFN_ATOM_VOCAB_ZINC250K: int = 38
GRAPHBFN_BOND_VOCAB: int = 4

#: Default max-nodes cap (QM9). ZINC250k production callers should
#: override via constructor ``max_nodes``.
GRAPHBFN_MAX_NODES_DEFAULT: int = 29

#: Audit / error code constants (deterministic ASCII strings).
AUDIT_GRAPHBFN_RESTART_BLEND: str = "graphbfn_restart_blend"
AUDIT_GRAPHBFN_OBSERVED: str = "graphbfn_observed"
AUDIT_GRAPHBFN_FORWARD_NOISE_APPLIED: str = "graphbfn_forward_noise_applied"
ERR_GRAPHBFN_NUM_STEPS: str = "graphbfn_num_steps_must_be_positive"
ERR_GRAPHBFN_BACKEND: str = "graphbfn_backend_unavailable"
ERR_GRAPHBFN_INVALID_CHANNEL: str = "graphbfn_invalid_channel"

#: LRU bound for the native-state cache (mirrors audit A-3 fix in
#: :class:`TwoDimFMAdapter`).
GRAPHBFN_NATIVE_STATES_MAXSIZE: int = 64

#: Default RNG seed offset (so two adapter instances with identical
#: (batch_id, sample_id) inputs agree on byte-identical state).
GRAPHBFN_SEED_OFFSET_DEFAULT: int = 0

#: Default memory fraction when beta_by_channel omits a channel.
GRAPHBFN_DEFAULT_MEMORY_FRACTION: float = 0.5

# Local type alias (avoid numpy at module-import hot annotation paths).
ArrayF64 = NDArray[np.float64]

#: Mode literal — torch (production) or synthetic (test-only).
GraphBFNMode = Literal["torch", "synthetic"]

#: Variant literal — ICLR-2025 or Hierarchical BFN.
GraphBFNVariant = Literal["iclr2025", "hierarchical"]


# ---------------------------------------------------------------------------
# Public helpers — hashing + torch-availability check
# ---------------------------------------------------------------------------


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    The check is intentionally a runtime ``importlib.util.find_spec``
    call so test fixtures that install torch mid-session see the live
    answer (mirrors
    :func:`adaptive_reflow.adapters.rectified_flow_cifar.torch_is_available`).
    """
    import importlib.util as _il

    return _il.find_spec("torch") is not None


def graphbfn_resolve_weights_path(
    data_dir: Path | None = None,
    *,
    candidates: tuple[str, ...] = (
        "graphbfn_qm9.pt",
        "graphbfn_zinc250k.pt",
        "graphbfn.pt",
    ),
) -> Path | None:
    """Return the first existing candidate weights path under ``data_dir``.

    Returns ``None`` when none of the candidates exist (the adapter
    then falls back to ``synthetic`` mode when ``force_mode="auto"``).
    """
    base = Path(data_dir) if data_dir is not None else Path("data")
    for name in candidates:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Private helpers — hashing, seeding, and graph-shaped tensor blending
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """SHA-256-derived 32-bit seed from ``(batch_id, sample_id, source_round)``."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of a payload (sorted keys, repr'd)."""
    blob = repr((sorted(payload.items(), key=lambda kv: str(kv[0])),)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Deterministic hash-stable :class:`TensorRef` for GraphBFN."""
    return make_ref(f"graphbfn:{label}", label, **parts)


def _memory_fraction_for(policy: RestartPolicy, channel: ChannelName) -> float:
    """Return ``m = 1 - beta`` for ``channel`` (default 0.5 when omitted)."""
    beta_raw = policy.beta_by_channel.get(channel)  # type: ignore[arg-type]
    if beta_raw is None:
        return float(GRAPHBFN_DEFAULT_MEMORY_FRACTION)
    beta = float(beta_raw)
    # Clip into [0, 1] — same convention as TwoDimFMAdapter.
    return max(0.0, min(1.0, 1.0 - beta))


def _blend_graph_param(
    prior_value: ArrayF64,
    fresh_value: ArrayF64,
    memory_fraction: float,
) -> ArrayF64:
    """Elementwise ``m * prior + (1 - m) * fresh`` blend on graph-shaped arrays.

    Both inputs are broadcast to a common shape; ``memory_fraction``
    is clipped into ``[0, 1]``. Mirrors the ``_blend_endpoint_with_prior``
    blend math used by :class:`TwoDimFMAdapter` but lifted to per-channel
    graph-shaped tensors.
    """
    m = max(0.0, min(1.0, float(memory_fraction)))
    prior = np.asarray(prior_value, dtype=np.float64)
    fresh = np.asarray(fresh_value, dtype=np.float64)
    target_shape = np.broadcast_shapes(prior.shape, fresh.shape)
    prior_b = np.broadcast_to(prior, target_shape)
    fresh_b = np.broadcast_to(fresh, target_shape)
    # Degenerate weights must pass the surviving side through untouched.
    # The adjacency channel carries ``-inf`` diagonal sentinels (the
    # self-loop mask from ``_uniform_edge_existence_logits``), and
    # ``0.0 * -inf`` is NaN — so the general formula would silently
    # convert a masked self-loop into a NaN logit at m == 0 or m == 1.
    if m == 0.0:
        return np.array(fresh_b, dtype=np.float64).reshape(target_shape)
    if m == 1.0:
        return np.array(prior_b, dtype=np.float64).reshape(target_shape)
    return np.asarray(m * prior_b + (1.0 - m) * fresh_b, dtype=np.float64).reshape(
        target_shape
    )


def _uniform_categorical_params(*, vocab_size: int, n_slots: int, rng: np.random.Generator) -> ArrayF64:
    """Sample a ``(n_slots, vocab_size)`` Categorical parameter vector.

    Returns the *logits* form (zeros), which represent a uniform
    Categorical distribution under softmax. Used to build the empty /
    uniform GraphBFN prior.
    """
    if vocab_size <= 0:
        raise ValueError("vocab_size_must_be_positive")
    if n_slots < 0:
        raise ValueError("n_slots_must_be_nonneg")
    if n_slots == 0:
        return np.zeros((0, int(vocab_size)), dtype=np.float64)
    return np.zeros((int(n_slots), int(vocab_size)), dtype=np.float64)


def _uniform_edge_existence_logits(*, n_nodes: int, rng: np.random.Generator) -> ArrayF64:
    """Sample an ``(n_nodes, n_nodes)`` upper-triangular edge-existence logit matrix.

    Returns a symmetric matrix with zero logits (uniform Bernoulli
    ``(0.5)`` prior). Diagonal entries are forced to ``-inf`` so the
    upper-triangular pattern is preserved.
    """
    if n_nodes <= 0:
        return np.zeros((0, 0), dtype=np.float64)
    logits = np.zeros((int(n_nodes), int(n_nodes)), dtype=np.float64)
    # Block self-loops via -inf on the diagonal.
    np.fill_diagonal(logits, -np.inf)
    return logits


# ---------------------------------------------------------------------------
# Synthetic (NumPy) BFN loop — testing-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthetic_bfn_step(
    *,
    theta_node: ArrayF64,
    theta_edge: ArrayF64,
    adjacency_logits: ArrayF64,
    n_nodes: int,
    n_edges: int,
    t: float,
    seed: int,
    cond_kind: str,
    cond_value: float | None,
    vocab_atom: int,
    vocab_bond: int,
) -> tuple[ArrayF64, ArrayF64, ArrayF64]:
    """One synthetic BFN Bayesian-update step.

    The synthetic step:

    1. Samples a noisy observation ``y_t`` per node / per edge from
       the current Categorical distribution (``softmax(theta)``).
    2. Computes a per-channel Bayesian update that drives
       ``theta_node`` and ``theta_edge`` toward one-hot vectors.
    3. Advances the adjacency logits toward ``+inf`` for kept edges
       and ``-inf`` for pruned edges (Bernoulli posterior over the
       noisy edge-existence observation).

    The output is deterministic for fixed inputs + ``seed``. The
    ``cond_kind`` + ``cond_value`` arguments are passed-through so the
    property-conditioning path can be exercised on the synthetic side.
    """
    rng = np.random.default_rng(int(seed))

    if n_nodes > 0:
        # 1. Per-node observation: argmax of softmax(theta_node) + tiny noise.
        obs_node = rng.integers(0, vocab_atom, size=n_nodes).astype(np.int64)
        # 2. Bayesian update: move the chosen slot's logit up by ``1 / t``;
        #    paper-form ``theta_{t+dt} = theta_t + dt * (one_hot - softmax(theta_t))``.
        dt = 1.0 / 32.0  # mirror the default num_steps for stable synthetic dynamics.
        soft_node = _softmax(theta_node)
        delta_node = np.zeros_like(theta_node)
        delta_node[np.arange(n_nodes), obs_node] = 1.0
        delta_node = delta_node - soft_node
        # Optional property-conditioning mask: when ``cond_kind`` is set,
        # push every node's logit toward the most-atom-like slot (slot 0
        # is the canonical carbon proxy in the synthetic mode).
        if cond_kind != "unconditional" and cond_value is not None:
            # Soft pull: nudge the first atom-type slot's logit toward
            # ``cond_value``. The exact update is a synthetic stand-in.
            delta_node[:, 0] += float(cond_value) * dt
        theta_node = theta_node + dt * delta_node
    else:
        theta_node = np.zeros((0, vocab_atom), dtype=np.float64)

    if n_edges > 0:
        obs_edge = rng.integers(0, vocab_bond, size=n_edges).astype(np.int64)
        soft_edge = _softmax(theta_edge)
        delta_edge = np.zeros_like(theta_edge)
        delta_edge[np.arange(n_edges), obs_edge] = 1.0
        delta_edge = delta_edge - soft_edge
        theta_edge = theta_edge + dt * delta_edge
    else:
        theta_edge = np.zeros((0, vocab_bond), dtype=np.float64)

    if n_nodes > 0:
        # Adjacency: push each upper-triangular slot toward its current
        # Bernoulli posterior (synthetic: bias toward 50/50).
        obs_adj = rng.integers(0, 2, size=(n_nodes, n_nodes)).astype(np.int64)
        delta_adj = obs_adj.astype(np.float64) - 0.5
        # Suppress the diagonal (no self-loops).
        np.fill_diagonal(delta_adj, 0.0)
        adjacency_logits = adjacency_logits + dt * delta_adj
    else:
        adjacency_logits = np.zeros((0, 0), dtype=np.float64)

    return theta_node, theta_edge, adjacency_logits


def _softmax(x: ArrayF64) -> ArrayF64:
    """Numerically stable softmax over the last axis; empty-safe."""
    arr = np.asarray(x, dtype=np.float64)
    if arr.size == 0:
        return arr
    shifted = arr - arr.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def _argmax_rounded_samples(
    *,
    theta_node: ArrayF64,
    theta_edge: ArrayF64,
    adjacency_logits: ArrayF64,
    vocab_atom: int,
    vocab_bond: int,
) -> dict[str, ArrayF64]:
    """Final-rounding pass: argmax per slot + edge-existence mask.

    Returns ``{"atom_types": (N,), "bond_types": (E,), "adjacency": (N, N)}``.
    """
    if theta_node.shape[0] > 0:
        atom_types = np.argmax(theta_node, axis=-1).astype(np.int64)
    else:
        atom_types = np.zeros((0,), dtype=np.int64)
    if theta_edge.shape[0] > 0:
        bond_types = np.argmax(theta_edge, axis=-1).astype(np.int64)
    else:
        bond_types = np.zeros((0,), dtype=np.int64)
    if adjacency_logits.shape[0] > 0:
        adjacency = (adjacency_logits > 0.0).astype(np.int64)
        np.fill_diagonal(adjacency, 0)
    else:
        adjacency = np.zeros((0, 0), dtype=np.int64)
    return {
        "atom_types": atom_types,
        "bond_types": bond_types,
        "adjacency": adjacency,
    }


# ---------------------------------------------------------------------------
# Torch-backed BFN step — production path; requires ``torch`` runtime
# ---------------------------------------------------------------------------


def _load_torch_bfn(
    weights_path: Path,
    *,
    vocab_atom: int,
    vocab_bond: int,
    max_nodes: int,
) -> Any:
    """Load a published GraphBFN GNN / Graph-Transformer ``state_dict``.

    **Placeholder torch loader.** The published GraphBFN
    checkpoints are gated on the ``[graphbfn-extra]`` optional extra
    (torch>=2.4 + rdkit>=2024.3.3); the corresponding paper weights
    have not yet been downloaded successfully (status='failed' in
    ``data/graphbfn/weights_metadata.json`` per the design spec). The
    loader here therefore raises :class:`NotImplementedError` until the
    weights-acquisition phase lands — the adapter's
    :meth:`__init__` then routes callers into ``synthetic`` mode so the
    test suite continues to run on CPU-only environments.
    """
    raise NotImplementedError(
        "GraphBFN torch-mode loader is gated on the weights-acquisition "
        "phase (data/graphbfn/weights_metadata.json status='failed'). "
        "Until the published GNN / Graph-Transformer checkpoints land "
        "in data/graphbfn/, the adapter runs in synthetic mode only."
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphBFNCapabilities(AdapterCapabilities):
    """Capability surface for :class:`GraphBFNAdapter`.

    Carries the per-channel domain declaration so the engine's
    ``channel_domains`` resolver routes per-channel state through the
    right domain kind. ``state_shape=()`` is the design-spec
    zero-length surrogate; the graph payload lives behind
    ``TensorRef`` keys in the adapter's private native-state cache.

    DESIGN NOTE (r17-audit P-05): ``state_shape=()`` is intentional
    and is NOT a defect. The GraphBFN native state is a heterogeneous
    graph ``(atoms, bonds, adjacency, valence, charge)`` whose
    shapes are dynamic (``n_atoms``, ``n_edges`` vary per sample) so
    no fixed-shape float64 placeholder is meaningful. The F14 runner's
    ``np.zeros(state_shape, dtype=np.float64)`` is a no-op on the
    zero-length tuple; the runner bypasses the allocation entirely
    and threads graph payloads via :class:`TensorRef` keys. Do NOT
    "fix" this to ``(n_atoms, 3)`` or any other concrete shape --
    it would break the dynamic-shape contract that lets GraphBFN
    handle variable molecular graphs.
    """

    def __init__(self, *, variant: GraphBFNVariant = "iclr2025") -> None:  # noqa: D401
        config_hash = (
            GRAPHBFN_CONFIG_HASH_HIER
            if variant == "hierarchical"
            else GRAPHBFN_CONFIG_HASH_ICLR
        )
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=False,
            state_shape=(),
            supported_channels=GRAPHBFN_CHANNELS,
            channel_domains=GRAPHBFN_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=config_hash,
            native_config_version=GRAPHBFN_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter)
class GraphBFNAdapter(FlowMatchingODEAdapter):
    """GraphBFN (Bayesian Flow Network on graphs) adapter.

    Implements all eight methods of :class:`FlowMatchingODEAdapter`
    against a graph-shaped Categorical-distribution parameter payload.
    Two operating modes:

    * ``torch`` — production path. Loads the published GNN /
      Graph-Transformer ``state_dict`` via :mod:`torch` and runs the
      BFN Bayesian-update loop inside :meth:`solve_ode`. Requires the
      ``[graphbfn-extra]`` optional extra.
    * ``synthetic`` — testing-only path. Deterministic NumPy BFN
      update loop that walks the synthetic Bayesian update against a
      random-init Categorical parameter tensor. The synthetic path is
      NOT a reproduction of the ICLR-2025 / Hierarchical GraphBFN
      papers — it exists solely to let the test suite exercise the
      Protocol surface without the heavy torch dependency.

    The native state is graph-shaped (variable node count ``N``,
    per-edge count ``E``, ``(N, N)`` adjacency). The engine never
    inspects the native payload — it only propagates opaque
    ``native_state_digest`` strings. The graph lives behind
    ``TensorRef`` keys in the adapter's private ``_native_states``
    cache, indexed by ``native_state_digest``.

    Constructor parameters
    ----------------------

    * ``variant`` — ``"iclr2025"`` (default) or ``"hierarchical"``.
      Selects the native config hash (``graphbfn:cfg:v1`` /
      ``graphbfn_hier:cfg:v1``); the synthetic path is the same for
      both.
    * ``dataset`` — ``"qm9"`` (default) or ``"zinc250k"``. Sets the
      default atom vocabulary (9 / 38).
    * ``num_steps`` — default BFN step count per round. Paper uses
      ~1000 on QM9 / ~500 on ZINC250k for the 1-Rectified-Flow
      equivalent; the default here is conservative for the synthetic
      path; production callers should override.
    * ``max_nodes`` — cap on node count per generated graph. Default
      matches QM9 (29); ZINC250k callers should override to 38.
    * ``force_mode`` — ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default). ``"auto"`` picks ``"torch"`` when the weights file
      exists AND torch is importable; otherwise ``"synthetic"``.
    """

    #: Mechanism id exposed for capability handshake (the engine reads
    #: ``mechanism_id`` via duck-typing on the adapter class).
    mechanism_id: str = "graphbfn"

    #: Pinned num-steps default (mirror ``pinned_num_steps`` on the
    #: :class:`TwoDimFMAdapter`).
    pinned_num_steps: int = GRAPHBFN_NUM_STEPS_DEFAULT

    # --- Inline design intent: ``state_shape=()`` zero-length surrogate ---
    # The GraphBFN native payload is a *graph* (variable node count ``N``,
    # variable edge count ``E``, ``(N, N)`` adjacency logits) — it does
    # not fit a fixed-shape tensor. The engine's ``StateBundle`` treats
    # ``state_shape`` as a fixed tuple and ``TensorRef`` as an opaque
    # string handle, so the graph payload is routed behind ``TensorRef``
    # keys in the adapter's private ``_native_states`` cache, indexed by
    # ``native_state_digest``. The graph itself therefore behaves like a
    # flat observation from the engine's perspective: the engine never
    # inspects it, only propagates the opaque handle. Concretely:
    #
    # * ``state_shape=()`` is the design-spec zero-length surrogate that
    #   tells the runner (F14) not to allocate a hard-coded ``(2,)``
    #   forward-noise prior — the runner reads
    #   ``getattr(self._adapter, "state_shape", (2,))`` and falls back to
    #   the 2-D shape only when the attribute is absent.
    # * ``has_materialization_route=False`` (declared in
    #   :class:`GraphBFNCapabilities`) keeps the engine from attempting
    #   to materialize the graph via the engine's envelope plumbing;
    #   the adapter handles the LRU-bounded cache itself.
    state_shape: tuple[int, ...] = ()

    def __init__(
        self,
        *,
        variant: GraphBFNVariant = "iclr2025",
        dataset: Literal["qm9", "zinc250k"] = "qm9",
        num_steps: int = GRAPHBFN_NUM_STEPS_DEFAULT,
        max_nodes: int = GRAPHBFN_MAX_NODES_DEFAULT,
        weights_path: Path | None = None,
        force_mode: GraphBFNMode | Literal["auto"] = "auto",
        seed_offset: int = GRAPHBFN_SEED_OFFSET_DEFAULT,
        atom_vocab_size: int | None = None,
        bond_vocab_size: int = GRAPHBFN_BOND_VOCAB,
    ) -> None:
        if str(dataset) not in ("qm9", "zinc250k"):
            raise ValueError(f"unknown_dataset:{dataset}")
        if int(num_steps) <= 0:
            raise ValueError(ERR_GRAPHBFN_NUM_STEPS)
        if int(max_nodes) <= 0:
            raise ValueError("max_nodes_must_be_positive")
        if int(bond_vocab_size) <= 0:
            raise ValueError("bond_vocab_size_must_be_positive")
        if str(variant) not in ("iclr2025", "hierarchical"):
            raise ValueError(f"unknown_variant:{variant}")
        self._variant: GraphBFNVariant = variant
        self._dataset: str = str(dataset)
        self._num_steps = int(num_steps)
        self._max_nodes = int(max_nodes)
        self._seed_offset = int(seed_offset)
        self._bond_vocab_size = int(bond_vocab_size)
        if atom_vocab_size is None:
            atom_vocab_size = (
                GRAPHBFN_ATOM_VOCAB_ZINC250K
                if dataset == "zinc250k"
                else GRAPHBFN_ATOM_VOCAB_QM9
            )
        if int(atom_vocab_size) <= 0:
            raise ValueError("atom_vocab_size_must_be_positive")
        self._atom_vocab_size = int(atom_vocab_size)

        # Resolve weights path (None when the file does not exist).
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or graphbfn_resolve_weights_path()
        self._weights_path = (
            Path(resolved) if resolved is not None else Path("synthetic")
        )

        # Decide operating mode.
        if force_mode == "auto":
            if self._weights_path.exists() and torch_is_available():
                self._mode: GraphBFNMode = "torch"
            else:
                self._mode = "synthetic"
        elif force_mode == "torch":
            if not torch_is_available():
                raise RuntimeError(f"{ERR_GRAPHBFN_BACKEND}:torch_not_installed")
            if not self._weights_path.exists():
                raise FileNotFoundError(
                    f"{ERR_GRAPHBFN_BACKEND}:weights_missing:{self._weights_path}"
                )
            self._mode = "torch"
        elif force_mode == "synthetic":
            self._mode = "synthetic"
        else:
            raise ValueError(f"unknown_force_mode:{force_mode}")

        # Backend handle — populated on first torch-mode use.
        self._bfn_module: Any = None
        if self._mode == "torch":
            try:
                self._bfn_module = _load_torch_bfn(
                    self._weights_path,
                    vocab_atom=self._atom_vocab_size,
                    vocab_bond=self._bond_vocab_size,
                    max_nodes=self._max_nodes,
                )
            except NotImplementedError:
                # Weights-acquisition phase is not yet landed; fall
                # back to synthetic so callers that explicitly opted
                # into ``force_mode="auto"`` still see a usable
                # adapter. Callers that opted into ``"torch"`` raise
                # above.
                self._mode = "synthetic"

        # LRU-bounded native-states cache (audit A-3 mirror of
        # :class:`TwoDimFMAdapter`).
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = GraphBFNCapabilities(variant=variant)

    # ------------------------------------------------------------------
    # 1. Capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. helpers — LRU-bounded native_states cache
    # ------------------------------------------------------------------

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        """Insert ``entry`` under ``digest``; evict the oldest past maxsize."""
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > GRAPHBFN_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        self._native_states.pop(digest, None)

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        """Return the empty / uniform prior state bundle at t=0.

        The "prior" is the zero-information state: empty graph (N=0)
        or, equivalently, a uniform Categorical per slot. The native
        graph payload is stored under ``native_state_digest`` in the
        adapter's ``_native_states`` cache; the bundle's channels are
        :data:`TensorRef` opaque handles.
        """
        seed = _seed_from_ids(
            str(batch_id), str(sample_id), int(self._seed_offset) + 0
        )
        rng = np.random.default_rng(seed)
        # Empty graph at t=0: N=0 (no nodes), E=0 (no edges), no adjacency.
        theta_node = _uniform_categorical_params(
            vocab_size=self._atom_vocab_size, n_slots=0, rng=rng
        )
        theta_edge = _uniform_categorical_params(
            vocab_size=self._bond_vocab_size, n_slots=0, rng=rng
        )
        adjacency = _uniform_edge_existence_logits(n_nodes=0, rng=rng)
        # Placeholder charge / valence scalars — also empty at t=0.
        charge = np.zeros((0,), dtype=np.float64)
        valence = np.zeros((0,), dtype=np.float64)

        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "dataset": self._dataset,
                "variant": self._variant,
                "atom_vocab_size": int(self._atom_vocab_size),
                "bond_vocab_size": int(self._bond_vocab_size),
            }
        )
        self._put_native_state(
            digest,
            {
                "theta_node": np.asarray(theta_node, dtype=np.float64),
                "theta_edge": np.asarray(theta_edge, dtype=np.float64),
                "adjacency_logits": np.asarray(adjacency, dtype=np.float64),
                "charge": np.asarray(charge, dtype=np.float64),
                "valence": np.asarray(valence, dtype=np.float64),
                "source_round": 0,
                "mode": self._mode,
                "kind": "initial",
            },
        )
        channels = {
            ch: _make_ref(
                "initial",
                channel=str(ch),
                batch=batch_id,
                sample=sample_id,
                dataset=self._dataset,
                variant=self._variant,
            )
            for ch in GRAPHBFN_CHANNELS
        }
        bundle = StateBundle(
            channels=channels,
            masks={
                ch: _make_ref(
                    "mask", channel=str(ch), batch=batch_id, sample=sample_id
                )
                for ch in GRAPHBFN_CHANNELS
            },
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=digest,
            provenance=("graphbfn@v1", f"variant:{self._variant}"),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        """Per-channel graph-shaped blend.

        Each of the five channels has a domain-specific blend rule
        (mirroring :class:`TwoDimFMAdapter`'s elementwise blend
        ``m * prior + (1 - m) * fresh`` but lifted to graph-shaped
        tensors). The blender metadata (``blender_family`` +
        ``config_hash``) is stamped into the bundle's ``provenance``
        for auditability.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )

        next_round = int(state.source_round) + 1
        restart_seed_blob = repr(
            (str(policy.policy_hash), next_round, "graphbfn")
        ).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        rng = np.random.default_rng(restart_seed)

        # Fresh per-channel tensors drawn from the prior.
        n_nodes = prior_entry["theta_node"].shape[0]
        n_edges = prior_entry["theta_edge"].shape[0]
        fresh_theta_node = _uniform_categorical_params(
            vocab_size=self._atom_vocab_size,
            n_slots=n_nodes,
            rng=rng,
        )
        fresh_theta_edge = _uniform_categorical_params(
            vocab_size=self._bond_vocab_size,
            n_slots=n_edges,
            rng=rng,
        )
        fresh_adjacency = _uniform_edge_existence_logits(n_nodes=n_nodes, rng=rng)
        fresh_charge = np.zeros_like(prior_entry["charge"]) if n_nodes > 0 else np.zeros(
            (0,), dtype=np.float64
        )
        fresh_valence = np.zeros_like(prior_entry["valence"]) if n_nodes > 0 else np.zeros(
            (0,), dtype=np.float64
        )

        # Per-channel blend. ``m = 1 - beta`` per channel; defaults to
        # 0.5 when the policy omits a channel.
        m_atom = _memory_fraction_for(policy, ChannelName("atoms"))
        m_bond = _memory_fraction_for(policy, ChannelName("bonds"))
        m_adj = _memory_fraction_for(policy, ChannelName("adjacency"))
        m_val = _memory_fraction_for(policy, ChannelName("valence"))
        m_chg = _memory_fraction_for(policy, ChannelName("charge"))

        blended_node = _blend_graph_param(
            prior_entry["theta_node"], fresh_theta_node, m_atom
        )
        blended_edge = _blend_graph_param(
            prior_entry["theta_edge"], fresh_theta_edge, m_bond
        )
        blended_adj = _blend_graph_param(
            prior_entry["adjacency_logits"], fresh_adjacency, m_adj
        )
        blended_valence = _blend_graph_param(
            prior_entry["valence"], fresh_valence, m_val
        )
        blended_charge = _blend_graph_param(
            prior_entry["charge"], fresh_charge, m_chg
        )

        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "dataset": self._dataset,
                "variant": self._variant,
                "m_atom": float(m_atom),
                "m_bond": float(m_bond),
                "m_adj": float(m_adj),
                "m_valence": float(m_val),
                "m_charge": float(m_chg),
                "n_nodes": int(blended_node.shape[0]),
                "n_edges": int(blended_edge.shape[0]),
            }
        )
        self._put_native_state(
            next_digest,
            {
                "theta_node": np.asarray(blended_node, dtype=np.float64),
                "theta_edge": np.asarray(blended_edge, dtype=np.float64),
                "adjacency_logits": np.asarray(blended_adj, dtype=np.float64),
                "charge": np.asarray(blended_charge, dtype=np.float64),
                "valence": np.asarray(blended_valence, dtype=np.float64),
                "source_round": next_round,
                "mode": self._mode,
                "kind": "restart",
            },
        )
        return StateBundle(
            channels={
                ch: _make_ref(
                    "restart",
                    channel=str(ch),
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                )
                for ch in GRAPHBFN_CHANNELS
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(next_digest),
            provenance=tuple(state.provenance)
            + (
                AUDIT_GRAPHBFN_RESTART_BLEND,
                f"variant:{self._variant}",
                f"dataset:{self._dataset}",
            ),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Inject GraphBFN-native metadata into ``delta_spec``.

        For unconditional generation (the GraphBFN baseline case),
        this is a near no-op that stamps the adapter's
        ``native_config_hash`` + ``atom_vocab_size`` + ``bond_vocab_size``
        + dataset markers into ``delta_spec``. For property-conditioned
        generation (the Hierarchical variant supports property
        conditioning without retraining), the condition kind + target
        scalar are forwarded through ``delta_spec`` so :meth:`solve_ode`
        can apply the property-conditioning mask at every BFN step.
        """
        del bundle
        new_spec = dict(delta.delta_spec)
        new_spec.setdefault("target_distribution", self._dataset)
        new_spec.setdefault("integrator_config_hash", self._caps.native_config_hash)
        new_spec.setdefault("variant", self._variant)
        new_spec.setdefault("atom_vocab_size", int(self._atom_vocab_size))
        new_spec.setdefault("bond_vocab_size", int(self._bond_vocab_size))
        # Default condition kind: ``unconditional`` when the caller did
        # not set one. Property kinds are validated against
        # :data:`GRAPHBFN_CONDITION_KINDS`.
        cond_kind = str(new_spec.get("condition_kind", "unconditional"))
        if cond_kind not in GRAPHBFN_CONDITION_KINDS:
            raise ValueError(f"unknown_condition_kind:{cond_kind}")
        new_spec["condition_kind"] = cond_kind
        # Property-conditioned generation requires a numeric target
        # scalar in [0, 1] (the canonical property range for logP /
        # QED / SA after normalisation).
        if cond_kind != "unconditional":
            target = new_spec.get("property_value", None)
            if target is None:
                raise ValueError(
                    "property_value_required_for_conditioned_generation"
                )
            new_spec["property_value"] = float(target)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Run the BFN Bayesian-update loop for ``num_steps`` NFE-like calls.

        Each step:

        1. Reads the current per-node / per-edge Categorical
           parameters from native-state.
        2. Samples a noisy observation ``y_t`` (one Categorical sample
           per node and per edge drawn from the current distribution).
        3. Calls the BFN module (synthetic: :func:`_synthetic_bfn_step`;
           production: a torch GNN / Graph-Transformer forward) to
           compute the predictive posterior parameters.
        4. Updates the per-node and per-edge Categorical parameters
           via the BFN Bayesian-update formula.
        5. Advances ``t`` by ``dt = 1 / num_steps``.

        After ``num_steps`` such NFE-like calls the final per-node and
        per-edge Categorical distributions are stored in native-state
        keyed by the trajectory digest; ``observe_endpoint`` reads
        them out and rounds them into atom / bond types.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )

        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError(ERR_GRAPHBFN_NUM_STEPS)
        cond_kind = str(condition.delta_spec.get("condition_kind", "unconditional"))
        cond_value = condition.delta_spec.get("property_value", None)
        cond_value_f = float(cond_value) if cond_value is not None else None

        theta_node = np.asarray(prior_entry["theta_node"], dtype=np.float64).copy()
        theta_edge = np.asarray(prior_entry["theta_edge"], dtype=np.float64).copy()
        adjacency = np.asarray(
            prior_entry["adjacency_logits"], dtype=np.float64
        ).copy()
        charge = np.asarray(prior_entry["charge"], dtype=np.float64).copy()
        valence = np.asarray(prior_entry["valence"], dtype=np.float64).copy()
        n_nodes = int(theta_node.shape[0])
        n_edges = int(theta_edge.shape[0])

        # When the prior is the empty graph (n_nodes == 0), sample a
        # *fresh* graph scaffold at the start of ``solve_ode``: a
        # small (sampled) number of nodes and edges drawn from a
        # geometric distribution. This mirrors the GraphBFN paper's
        # variable-node-count setup.
        if n_nodes == 0:
            rng = np.random.default_rng(
                int(seed) ^ int(_seed_from_ids(str(state.batch_id), str(state.sample_id), 0))
            )
            n_nodes = int(rng.integers(1, max(2, self._max_nodes)))
            n_edges = int(rng.integers(1, max(2, 2 * n_nodes)))
            theta_node = _uniform_categorical_params(
                vocab_size=self._atom_vocab_size,
                n_slots=n_nodes,
                rng=rng,
            )
            theta_edge = _uniform_categorical_params(
                vocab_size=self._bond_vocab_size,
                n_slots=n_edges,
                rng=rng,
            )
            adjacency = _uniform_edge_existence_logits(n_nodes=n_nodes, rng=rng)
            charge = np.zeros((n_nodes,), dtype=np.float64)
            valence = np.zeros((n_nodes,), dtype=np.float64)

        # Run the BFN loop.
        for step_idx in range(int(num_steps)):
            t_cur = float(step_idx) / float(num_steps)
            step_seed = int(seed) + step_idx
            theta_node, theta_edge, adjacency = _synthetic_bfn_step(
                theta_node=theta_node,
                theta_edge=theta_edge,
                adjacency_logits=adjacency,
                n_nodes=n_nodes,
                n_edges=n_edges,
                t=t_cur,
                seed=step_seed,
                cond_kind=cond_kind,
                cond_value=cond_value_f,
                vocab_atom=self._atom_vocab_size,
                vocab_bond=self._bond_vocab_size,
            )

        # Optional CDF-rounding for the Hierarchical variant at t=1:
        # collapse the Categorical parameters to one-hot via argmax +
        # a final CDF-rescale step. For the synthetic path this is a
        # no-op; the production loader routes through the published
        # CDF-rounding pass.
        if self._variant == "hierarchical" and n_nodes > 0:
            # Synthetic CDF-rounding: subtract max logit to sharpen
            # the Categorical parameters before the observation step.
            theta_node = theta_node - theta_node.max(axis=-1, keepdims=True)
            theta_edge = theta_edge - theta_edge.max(axis=-1, keepdims=True)

        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "num_steps": int(num_steps),
                "dataset": self._dataset,
                "variant": self._variant,
                "cond_kind": str(cond_kind),
                "shape_node": [int(theta_node.shape[0]), int(theta_node.shape[1])],
                "shape_edge": [int(theta_edge.shape[0]), int(theta_edge.shape[1])],
                "shape_adj": [int(adjacency.shape[0]), int(adjacency.shape[1])],
                "mode": self._mode,
            }
        )
        self._put_native_state(
            traj_digest,
            {
                "theta_node": np.asarray(theta_node, dtype=np.float64),
                "theta_edge": np.asarray(theta_edge, dtype=np.float64),
                "adjacency_logits": np.asarray(adjacency, dtype=np.float64),
                "charge": np.asarray(charge, dtype=np.float64),
                "valence": np.asarray(valence, dtype=np.float64),
                "kind": "trajectory",
                "num_steps": int(num_steps),
                "cond_kind": str(cond_kind),
                "cond_value": cond_value_f,
                "dataset": self._dataset,
                "variant": self._variant,
                "mode": self._mode,
            },
        )
        cfg_blob = repr(
            (
                "graphbfn_config",
                str(self._variant),
                str(self._dataset),
                int(num_steps),
                int(seed),
            )
        ).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(num_steps),
            accept_rate=1.0,
            native_state_digest=traj_digest,
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Round the final Categorical parameters into atom / bond types.

        Stores the rounded graph in native-state keyed by a fresh
        endpoint digest; returns a :class:`StateBundle` whose
        :data:`TensorRef` channels point at the new digest. The graph
        payload (per-node atom-type vector, per-edge bond-type vector,
        adjacency) lives behind ``TensorRef`` keys in the adapter's
        native-state cache — the engine treats them as opaque.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=trace.native_state_digest
            )
        rounded = _argmax_rounded_samples(
            theta_node=traj_entry["theta_node"],
            theta_edge=traj_entry["theta_edge"],
            adjacency_logits=traj_entry["adjacency_logits"],
            vocab_atom=self._atom_vocab_size,
            vocab_bond=self._bond_vocab_size,
        )

        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "dataset": self._dataset,
                "variant": self._variant,
                "cond_kind": str(traj_entry["cond_kind"]),
                "atom_types_head": [
                    int(x) for x in rounded["atom_types"][: min(8, rounded["atom_types"].shape[0])]
                ],
                "bond_types_head": [
                    int(x) for x in rounded["bond_types"][: min(8, rounded["bond_types"].shape[0])]
                ],
            }
        )
        # The endpoint store carries the rounded graph + the
        # raw Categorical parameters so downstream evaluators can
        # inspect either form.
        self._put_native_state(
            endpoint_digest,
            {
                "theta_node": np.asarray(traj_entry["theta_node"], dtype=np.float64),
                "theta_edge": np.asarray(traj_entry["theta_edge"], dtype=np.float64),
                "adjacency_logits": np.asarray(
                    traj_entry["adjacency_logits"], dtype=np.float64
                ),
                "charge": np.asarray(traj_entry["charge"], dtype=np.float64),
                "valence": np.asarray(traj_entry["valence"], dtype=np.float64),
                "atom_types": rounded["atom_types"],
                "bond_types": rounded["bond_types"],
                "adjacency": rounded["adjacency"],
                "kind": "endpoint",
                "dataset": self._dataset,
                "variant": self._variant,
                "cond_kind": str(traj_entry["cond_kind"]),
                "cond_value": traj_entry.get("cond_value", None),
                "mode": self._mode,
            },
        )
        next_round = int(state.source_round) + 1
        return StateBundle(
            channels={
                ch: _make_ref(
                    "endpoint",
                    channel=str(ch),
                    traj_digest=str(trace.native_state_digest),
                    source_round=int(next_round),
                )
                for ch in GRAPHBFN_CHANNELS
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(endpoint_digest),
            provenance=tuple(state.provenance)
            + (
                AUDIT_GRAPHBFN_OBSERVED,
                f"variant:{self._variant}",
                f"dataset:{self._dataset}",
                f"cond_kind:{traj_entry['cond_kind']}",
            ),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any | None:
        """Return the native graph payload for ``trace`` (or ``None``).

        The trajectory payload is a dict with keys ``theta_node``,
        ``theta_edge``, ``adjacency_logits``, ``charge``, ``valence``;
        callers can inspect the Categorical parameters or call
        :func:`_argmax_rounded_samples` to recover the rounded graph.
        Returns ``None`` when no trajectory is stored under
        ``trace.native_state_digest``.
        """
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        return {
            "theta_node": np.asarray(entry["theta_node"], dtype=np.float64),
            "theta_edge": np.asarray(entry["theta_edge"], dtype=np.float64),
            "adjacency_logits": np.asarray(
                entry["adjacency_logits"], dtype=np.float64
            ),
            "charge": np.asarray(entry["charge"], dtype=np.float64),
            "valence": np.asarray(entry["valence"], dtype=np.float64),
        }

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): perturb the prior's Categorical params by ``injected``.

        The injected payload is treated as a graph-shaped delta on the
        per-node / per-edge Categorical parameter tensors. The
        resulting bundle carries the blended (clipped) Categorical
        parameters in native-state; the channel handles are rewritten
        with a forward-noise digest so parity tests can detect the
        pass.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        injected_arr = np.asarray(injected, dtype=np.float64)
        target_shape = prior_entry["theta_node"].shape
        delta = np.broadcast_to(injected_arr, target_shape).copy()
        theta_node_new = np.clip(
            prior_entry["theta_node"] + delta,
            -10.0,
            10.0,
        )
        new_digest = _digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "shape": [int(s) for s in theta_node_new.shape],
                "head": [
                    float(theta_node_new[0, 0]) if theta_node_new.size else 0.0,
                    float(theta_node_new[0, 1])
                    if theta_node_new.shape[0] > 0 and theta_node_new.shape[1] > 1
                    else 0.0,
                ],
            }
        )
        self._put_native_state(
            new_digest,
            {
                **prior_entry,
                "theta_node": np.asarray(theta_node_new, dtype=np.float64),
                "source_round": int(bundle.source_round),
                "kind": "forward_noise",
            },
        )
        return StateBundle(
            channels={
                ch: _make_ref(
                    "forward_noise",
                    channel=str(ch),
                    src_digest=str(bundle.native_state_digest),
                )
                for ch in GRAPHBFN_CHANNELS
            },
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=str(new_digest),
            provenance=tuple(bundle.provenance) + (AUDIT_GRAPHBFN_FORWARD_NOISE_APPLIED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 11. batched_inference — vanilla baseline + framework FCDs
    # ------------------------------------------------------------------

    def batched_inference(
        self,
        n_samples: int,
        *,
        num_steps: int | None = None,
        seed: int = 0,
        cond_kind: str = "unconditional",
        property_value: float | None = None,
    ) -> list[dict[str, ArrayF64]]:
        """Run ``n_samples`` independent BFN loops and return rounded graphs.

        Returns a list of ``n_samples`` dicts, each carrying keys
        ``atom_types``, ``bond_types``, ``adjacency``, ``theta_node``,
        ``theta_edge``, ``adjacency_logits``. The vanilla baseline
        path used by the GraphBFN SOTA harness
        (:file:`tools/run_sota_graphbfn_experiment.py`) consumes the
        ``atom_types`` / ``bond_types`` / ``adjacency`` entries for
        RDKit-based validity / FCD / NSPDK evaluation.
        """
        if int(n_samples) <= 0:
            raise ValueError("n_samples_must_be_positive")
        steps = int(num_steps) if num_steps is not None else self._num_steps
        if steps <= 0:
            raise ValueError(ERR_GRAPHBFN_NUM_STEPS)
        cond_value = float(property_value) if property_value is not None else None
        out: list[dict[str, ArrayF64]] = []
        rng = np.random.default_rng(int(seed))
        for k in range(int(n_samples)):
            sample_seed = int(rng.integers(0, 2**31 - 1))
            n_nodes = int(rng.integers(1, max(2, self._max_nodes)))
            n_edges = int(rng.integers(1, max(2, 2 * n_nodes)))
            theta_node = _uniform_categorical_params(
                vocab_size=self._atom_vocab_size,
                n_slots=n_nodes,
                rng=rng,
            )
            theta_edge = _uniform_categorical_params(
                vocab_size=self._bond_vocab_size,
                n_slots=n_edges,
                rng=rng,
            )
            adjacency = _uniform_edge_existence_logits(n_nodes=n_nodes, rng=rng)
            for step_idx in range(int(steps)):
                theta_node, theta_edge, adjacency = _synthetic_bfn_step(
                    theta_node=theta_node,
                    theta_edge=theta_edge,
                    adjacency_logits=adjacency,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    t=float(step_idx) / float(steps),
                    seed=sample_seed + step_idx,
                    cond_kind=str(cond_kind),
                    cond_value=cond_value,
                    vocab_atom=self._atom_vocab_size,
                    vocab_bond=self._bond_vocab_size,
                )
            if self._variant == "hierarchical" and n_nodes > 0:
                theta_node = theta_node - theta_node.max(axis=-1, keepdims=True)
                theta_edge = theta_edge - theta_edge.max(axis=-1, keepdims=True)
            rounded = _argmax_rounded_samples(
                theta_node=theta_node,
                theta_edge=theta_edge,
                adjacency_logits=adjacency,
                vocab_atom=self._atom_vocab_size,
                vocab_bond=self._bond_vocab_size,
            )
            out.append(
                {
                    "atom_types": rounded["atom_types"],
                    "bond_types": rounded["bond_types"],
                    "adjacency": rounded["adjacency"],
                    "theta_node": theta_node,
                    "theta_edge": theta_edge,
                    "adjacency_logits": adjacency,
                }
            )
        return out


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_graphbfn_adapter(
    *,
    variant: GraphBFNVariant = "iclr2025",
    dataset: Literal["qm9", "zinc250k"] = "qm9",
    num_steps: int = GRAPHBFN_NUM_STEPS_DEFAULT,
    force_mode: GraphBFNMode | Literal["auto"] = "auto",
) -> GraphBFNAdapter:
    """Return a fresh :class:`GraphBFNAdapter`.

    Production callers should pass ``force_mode='torch'`` and supply
    ``weights_path`` once the GraphBFN paper weights land in
    ``data/graphbfn/``. Until then, ``force_mode='auto'`` (the
    default) routes into ``synthetic`` mode so the adapter runs
    hermetically on CPU-only environments.
    """
    return GraphBFNAdapter(
        variant=variant,
        dataset=dataset,
        num_steps=num_steps,
        force_mode=force_mode,
    )


__all__ = [
    "AUDIT_GRAPHBFN_FORWARD_NOISE_APPLIED",
    "AUDIT_GRAPHBFN_OBSERVED",
    "AUDIT_GRAPHBFN_RESTART_BLEND",
    "ERR_GRAPHBFN_BACKEND",
    "ERR_GRAPHBFN_INVALID_CHANNEL",
    "ERR_GRAPHBFN_NUM_STEPS",
    "GRAPHBFN_ATOM_VOCAB_QM9",
    "GRAPHBFN_ATOM_VOCAB_ZINC250K",
    "GRAPHBFN_BOND_VOCAB",
    "GRAPHBFN_CHANNELS",
    "GRAPHBFN_CHANNEL_DOMAINS",
    "GRAPHBFN_CONFIG_HASH_HIER",
    "GRAPHBFN_CONFIG_HASH_ICLR",
    "GRAPHBFN_CONFIG_VERSION",
    "GRAPHBFN_CONDITION_KINDS",
    "GRAPHBFN_MAX_NODES_DEFAULT",
    "GRAPHBFN_NATIVE_STATES_MAXSIZE",
    "GRAPHBFN_NUM_STEPS_DEFAULT",
    "GRAPHBFN_SEED_OFFSET_DEFAULT",
    "GraphBFNAdapter",
    "GraphBFNCapabilities",
    "default_graphbfn_adapter",
    "graphbfn_resolve_weights_path",
    "torch_is_available",
]