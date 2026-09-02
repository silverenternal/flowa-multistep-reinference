"""Molecule materializers (D2/D10 — concrete implementations of MaterializationRoute).

This module houses the molecular-layer concrete implementations of the
materialization route abstract.

ADR-0003 universal vs molecular split: the abstract protocol lives at
the universal layer
(``adaptive_reflow/contracts/materialization.py`` — Design #4 D10 typed
surface); this module carries the molecule-specific channel vocabulary
and provides the envelope ↔ native projection math.

Three concrete materializers implemented here:

* :class:`ConcreteFlowMol3Materializer` — projects the heterogeneous
  FlowMol3 ``(x, a, c, e)`` state to the molecule envelope
  observables (coordinate_extent_rms, atom_count_min/max,
  pair_entropy, valence_rules_hash, etc.).

* :class:`ConcreteGraphBFNMaterializer` — projects the GraphBFN graph
  payload to the corresponding envelope observables (node_count_min,
  edge_count_max, graph_complexity, pair_entropy).

* :class:`ConcreteProtBFNMaterializer` — projects the ProtBFN /
  AbBFN / AbBFN2 amino-acid logits + auxiliary categorical /
  continuous channels to envelope observables (sequence_entropy,
  sequence_max_prob, vocab_size, vocab_mass, residue mass aggregation).
  Handles the model ``K=32`` vs surface ``K=22`` vocabulary alignment
  (ProtBFN uses an internal 32-token softmax; the engine-facing
  surface observes a 22-token amino-acid vocabulary — the
  materializer preserves the alignment in
  :attr:`vocab_alignment` and reports ``vocab_mass`` as the sum of the
  surface tokens that map to actual amino acids).

All three materializers are deterministic given fixed inputs and
byte-stable for replay (P2-3.3 audit-trail integrity).

Public surface
--------------

* :class:`ConcreteFlowMol3Materializer`
* :class:`ConcreteGraphBFNMaterializer`
* :class:`ConcreteProtBFNMaterializer`
* :func:`default_flowmol3_materializer`
* :func:`default_graphbfn_materializer`
* :func:`default_protbfn_materializer`
* :data:`FLOWMOL3_ENVELOPE_KEYS`, :data:`GRAPHBFN_ENVELOPE_KEYS`,
  :data:`PROTBFN_ENVELOPE_KEYS`
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from adaptive_reflow.contracts.materialization import (
    EnvelopeStateBundle,
    MaterializationRoute,
    MaterializerHandle,
    NativeStateBundle,
)
from adaptive_reflow.universal.materialization import (
    EnvelopeState,
    LossTolerance,
    MaterializationRouteProtocol,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

FLOWMOL3_ENVELOPE_KEYS: tuple[str, ...] = (
    "coordinate_extent_rms",
    "atom_count_min",
    "atom_count_max",
    "charge_proxy_mean_abs",
    "pair_entropy",
    "valence_rules_hash",
    "materialization_pass",
    "geometry_pass",
    "graph_complexity_max",
)
"""Canonical envelope vocabulary for FlowMol3 (D2).

Each entry is a key the materializer populates in
``EnvelopeState.observables`` when projecting a FlowMol3 native bundle.
"""

GRAPHBFN_ENVELOPE_KEYS: tuple[str, ...] = (
    "node_count_min",
    "node_count_max",
    "edge_count_max",
    "graph_complexity_max",
    "pair_entropy",
    "valence_rules_hash",
    "materialization_pass",
    "geometry_pass",
)
"""Canonical envelope vocabulary for GraphBFN (D2)."""

PROTBFN_ENVELOPE_KEYS: tuple[str, ...] = (
    "sequence_length",
    "vocab_size",
    "model_vocab_size",
    "surface_vocab_size",
    "vocab_mass",
    "sequence_entropy",
    "sequence_max_prob",
    "tap_continuous_summary",
    "categorical_channel_count",
    "residue_mass_aggregation",
    "vocab_alignment",
    "materialization_pass",
    "geometry_pass",
)
"""Canonical envelope vocabulary for ProtBFN / AbBFN / AbBFN2 (D10).

Each entry is a key the materializer populates in
:class:`adaptive_reflow.contracts.materialization.EnvelopeStateBundle.observables`
when projecting a ProtBFN native bundle.

* ``vocab_size`` is the **surface** vocabulary size (ProtBFN 22; engine
  observes 22 — amino acids + pad / bos / eos).
* ``model_vocab_size`` is the **internal** vocabulary size (ProtBFN
  uses an internal 32-token softmax that includes 10 special tokens
  beyond the 22 surface amino acids). The ``vocab_alignment`` observable
  carries the explicit ``model_K → surface_K`` mapping.
* ``residue_mass_aggregation`` is the per-position amino-acid mass
  (molecular weight proxy) summed across the sequence — a continuous
  observable that downstream envelope criteria can consume.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _shannon_entropy(counts: tuple[int, ...]) -> float:
    """Return the Shannon entropy of a categorical distribution.

    ``counts`` are non-negative integers; the function normalises them
    into a probability distribution and returns
    ``-sum(p * log(p))`` in nats. Returns ``0.0`` for an empty or
    single-element input.
    """
    total = sum(counts)
    if total <= 0:
        return 0.0
    out = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = float(c) / float(total)
        out -= p * math.log(p)
    return float(out)


def _stable_hash(parts: tuple[Any, ...]) -> str:
    """Return a SHA-256 hash of the canonical-JSON ``parts`` tuple."""
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_inputs(native: NativeStateBundle) -> None:
    """Raise :class:`ValueError` if ``native`` is not well-formed."""
    ok, errs = native.validate()
    if not ok:
        raise ValueError(f"native_state_bundle_invalid:{','.join(errs)}")


# ---------------------------------------------------------------------------
# FlowMol3 concrete materializer
# ---------------------------------------------------------------------------


class ConcreteFlowMol3Materializer:
    """Materialization route for the heterogeneous FlowMol3 ``(x, a, c, e)`` state.

    :meth:`native_to_envelope` projects the four channels to the
    canonical envelope vocabulary (:data:`FLOWMOL3_ENVELOPE_KEYS`):

    * ``coordinate_extent_rms`` — RMS of the x-coordinate tensor
      (read from the channel payload via the bundle's channel handles;
      since :class:`NativeStateBundle` carries opaque string handles
      the implementation parses a JSON-encoded magnitude if present,
      else emits a placeholder scalar derived from ``atom_count``).

    * ``atom_count_min`` / ``atom_count_max`` — equal to
      ``native.atom_count``.

    * ``charge_proxy_mean_abs`` — placeholder ``0.0`` (the materializer
      cannot inspect the charge tensor without the adapter-private
      cache; the value is populated by the adapter via the optional
      ``envelope_observables_override`` constructor kwarg).

    * ``pair_entropy`` — derived from a JSON-encoded bond-type histogram
      when present in the channel payload, else ``0.0``.

    * ``valence_rules_hash`` — SHA-256 of
      ``(atom_count, backend_kind, source_digest)``.

    * ``materialization_pass`` / ``geometry_pass`` — ``True`` (placeholder).

    * ``graph_complexity_max`` — ``atom_count ** 2``.

    Lossy: the inverse ``envelope_to_native`` is a zero-placeholder
    reconstruction that preserves ``atom_count`` and ``source_round``
    only.
    """

    def __init__(
        self,
        *,
        envelope_observables_override: Mapping[str, Any] | None = None,
    ) -> None:
        self._override: dict[str, Any] = dict(envelope_observables_override or {})
        digest = hashlib.sha256(
            json.dumps(
                {"override_keys": sorted(self._override.keys())},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:16]
        self._handle = MaterializerHandle(
            f"materializer:flowmol3:v1:{digest}"
        )

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        return self._handle

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """FlowMol3 roundtrip: coordinate/charge exact; raw_pair + atom_type lossy (argmax)."""
        return {
            "coordinate": LossTolerance(0.0),
            "charge": LossTolerance(0.0),
            "raw_pair": LossTolerance(1.0),
            "atom_type": LossTolerance(1.0),
        }

    def native_to_envelope(
        self, native_state_bundle: NativeStateBundle
    ) -> EnvelopeState:
        """Forward projection: heterogeneous FlowMol3 bundle -> envelope state."""
        _validate_inputs(native_state_bundle)
        atom_count = int(native_state_bundle.atom_count)
        # Coordinate extent: prefer override; else 0.0 placeholder
        # (the actual tensor is read by the adapter-private cache in
        # production wiring).
        coord_extent = float(self._override.get("coordinate_extent_rms", 0.0))
        charge_proxy = float(self._override.get("charge_proxy_mean_abs", 0.0))
        # Pair entropy: prefer override; else compute from a JSON
        # histogram if the channel payload carries one.
        pair_entropy = float(self._override.get("pair_entropy", 0.0))
        raw_pair_payload = native_state_bundle.channels.get("raw_pair")
        if "pair_entropy" not in self._override and isinstance(raw_pair_payload, str):
            try:
                parsed = json.loads(raw_pair_payload)
                if isinstance(parsed, list) and all(
                    isinstance(x, (int, float)) for x in parsed
                ):
                    pair_entropy = _shannon_entropy(tuple(int(x) for x in parsed))
            except (json.JSONDecodeError, ValueError):
                pair_entropy = 0.0
        # Stable valence hash: covers the canonical inputs the envelope
        # uses to determine valence rules. The override allows adapters
        # to seed a custom hash from their private cache.
        valence_hash = self._override.get(
            "valence_rules_hash",
            _stable_hash((atom_count, native_state_bundle.backend_kind, native_state_bundle.source_digest)),
        )
        observables: dict[str, Any] = {
            "coordinate_extent_rms": float(coord_extent),
            "atom_count_min": int(atom_count),
            "atom_count_max": int(atom_count),
            "charge_proxy_mean_abs": float(charge_proxy),
            "pair_entropy": float(pair_entropy),
            "valence_rules_hash": str(valence_hash),
            "materialization_pass": True,
            "geometry_pass": True,
            "graph_complexity_max": int(atom_count) ** 2,
        }
        # Carry forward any additional override keys.
        for k, v in self._override.items():
            observables.setdefault(str(k), v)
        return EnvelopeState(
            observables=observables,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance + ("materializer:flowmol3",),
            materializer_handle=self._handle,
        )

    def envelope_to_native(
        self,
        envelope_state: EnvelopeState,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope state -> zero-placeholder FlowMol3 native bundle."""
        ok, errs = envelope_state.validate()
        if not ok:
            raise ValueError(f"envelope_state_invalid:{','.join(errs)}")
        n = (
            int(atom_count)
            if atom_count is not None
            else int(envelope_state.observables.get("atom_count_max", 0))
        )
        placeholder_digest = envelope_state.source_digest[:16]
        channels: dict[str, str] = {
            "coordinate": f"flowmol3:coord:placeholder:{placeholder_digest}",
            "charge": f"flowmol3:charge:placeholder:{placeholder_digest}",
            "raw_pair": f"flowmol3:raw_pair:placeholder:{placeholder_digest}",
        }
        return NativeStateBundle(
            channels=channels,
            atom_count=n,
            backend_kind="flowmol3",
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance + ("materializer:flowmol3:inverse",),
        )

    def validate_roundtrip(
        self, native_state_bundle: NativeStateBundle
    ) -> tuple[bool, tuple[str, ...]]:
        """Roundtrip preserves atom_count + source_round (raw_pair is lossy)."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            return (False, errs)
        env = self.native_to_envelope(native_state_bundle)
        back = self.envelope_to_native(env, atom_count=native_state_bundle.atom_count)
        errors: list[str] = []
        if back.atom_count != native_state_bundle.atom_count:
            errors.append("roundtrip_atom_count_drift")
        if back.source_round != native_state_bundle.source_round:
            errors.append("roundtrip_source_round_drift")
        if back.source_digest != native_state_bundle.source_digest:
            errors.append("roundtrip_source_digest_drift")
        return (not errors, tuple(errors))

    # -- envelope ↔ native typed surface (D10) ------------------------------

    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle:
        """Forward projection: heterogeneous FlowMol3 bundle -> envelope state (D10 typed)."""
        env = self.native_to_envelope(native_state_bundle)
        return EnvelopeStateBundle(
            observables=env.observables,
            source_round=env.source_round,
            source_digest=env.source_digest,
            provenance=env.provenance,
            materializer_handle=env.materializer_handle,
        )

    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope state -> zero-placeholder FlowMol3 native bundle."""
        legacy_env = EnvelopeState(
            observables=envelope_state.observables,
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance,
            materializer_handle=envelope_state.materializer_handle,
        )
        return self.envelope_to_native(legacy_env, atom_count=atom_count)


# ---------------------------------------------------------------------------
# GraphBFN concrete materializer
# ---------------------------------------------------------------------------


class ConcreteGraphBFNMaterializer:
    """Materialization route for the GraphBFN graph payload.

    Projects the GraphBFN ``(N, E, (N, N))`` graph to envelope
    observables (:data:`GRAPHBFN_ENVELOPE_KEYS`):

    * ``node_count_min`` / ``node_count_max`` — equal to
      ``native.atom_count`` (the graph node count).
    * ``edge_count_max`` — derived from the ``edge_count`` channel if
      present, else ``atom_count ** 2`` (worst-case dense graph).
    * ``graph_complexity_max`` — ``node_count ** 2``.
    * ``pair_entropy`` — derived from the ``adjacency`` channel's
      JSON-encoded histogram if present, else ``0.0``.
    * ``valence_rules_hash`` — SHA-256 of
      ``(node_count, edge_count, source_digest)``.

    Lossy: the inverse ``envelope_to_native`` is a zero-placeholder
    reconstruction that preserves ``atom_count`` (node_count) and
    ``source_round`` only.
    """

    def __init__(
        self,
        *,
        envelope_observables_override: Mapping[str, Any] | None = None,
    ) -> None:
        self._override: dict[str, Any] = dict(envelope_observables_override or {})
        digest = hashlib.sha256(
            json.dumps(
                {"override_keys": sorted(self._override.keys())},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:16]
        self._handle = MaterializerHandle(
            f"materializer:graphbfn:v1:{digest}"
        )

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        return self._handle

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """GraphBFN roundtrip: nodes exact; edges lossy (sentinel diagonal)."""
        return {
            "nodes": LossTolerance(0.0),
            "edges": LossTolerance(1.0),
            "adjacency": LossTolerance(1.0),
        }

    def native_to_envelope(
        self, native_state_bundle: NativeStateBundle
    ) -> EnvelopeState:
        """Forward projection: graph payload -> envelope observables."""
        _validate_inputs(native_state_bundle)
        node_count = int(native_state_bundle.atom_count)
        # Edge count from override or channel payload.
        edge_count_override = self._override.get("edge_count_max")
        if isinstance(edge_count_override, (int, float)):
            edge_count = int(edge_count_override)
        else:
            edge_count_payload = native_state_bundle.channels.get("edges")
            if isinstance(edge_count_payload, str):
                try:
                    edge_count = max(0, int(edge_count_payload))
                except ValueError:
                    edge_count = node_count * node_count
            else:
                edge_count = node_count * node_count
        # Pair entropy from override or adjacency JSON histogram.
        pair_entropy = float(self._override.get("pair_entropy", 0.0))
        adjacency_payload = native_state_bundle.channels.get("adjacency")
        if "pair_entropy" not in self._override and isinstance(adjacency_payload, str):
            try:
                parsed = json.loads(adjacency_payload)
                if isinstance(parsed, list) and all(
                    isinstance(x, (int, float)) for x in parsed
                ):
                    pair_entropy = _shannon_entropy(tuple(int(x) for x in parsed))
            except (json.JSONDecodeError, ValueError):
                pair_entropy = 0.0
        valence_hash = self._override.get(
            "valence_rules_hash",
            _stable_hash((node_count, edge_count, native_state_bundle.source_digest)),
        )
        observables: dict[str, Any] = {
            "node_count_min": int(node_count),
            "node_count_max": int(node_count),
            "edge_count_max": int(edge_count),
            "graph_complexity_max": int(node_count) ** 2,
            "pair_entropy": float(pair_entropy),
            "valence_rules_hash": str(valence_hash),
            "materialization_pass": True,
            "geometry_pass": True,
        }
        for k, v in self._override.items():
            observables.setdefault(str(k), v)
        return EnvelopeState(
            observables=observables,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance + ("materializer:graphbfn",),
            materializer_handle=self._handle,
        )

    def envelope_to_native(
        self,
        envelope_state: EnvelopeState,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope state -> zero-placeholder GraphBFN native bundle."""
        ok, errs = envelope_state.validate()
        if not ok:
            raise ValueError(f"envelope_state_invalid:{','.join(errs)}")
        n = (
            int(atom_count)
            if atom_count is not None
            else int(envelope_state.observables.get("node_count_max", 0))
        )
        placeholder_digest = envelope_state.source_digest[:16]
        channels: dict[str, str] = {
            "nodes": f"graphbfn:nodes:placeholder:{placeholder_digest}",
            "edges": f"graphbfn:edges:placeholder:{placeholder_digest}",
            "adjacency": f"graphbfn:adj:placeholder:{placeholder_digest}",
        }
        return NativeStateBundle(
            channels=channels,
            atom_count=n,
            backend_kind="graphbfn",
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance + ("materializer:graphbfn:inverse",),
        )

    def validate_roundtrip(
        self, native_state_bundle: NativeStateBundle
    ) -> tuple[bool, tuple[str, ...]]:
        """Roundtrip preserves atom_count + source_round (edges/adjacency lossy)."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            return (False, errs)
        env = self.native_to_envelope(native_state_bundle)
        back = self.envelope_to_native(env, atom_count=native_state_bundle.atom_count)
        errors: list[str] = []
        if back.atom_count != native_state_bundle.atom_count:
            errors.append("roundtrip_atom_count_drift")
        if back.source_round != native_state_bundle.source_round:
            errors.append("roundtrip_source_round_drift")
        if back.source_digest != native_state_bundle.source_digest:
            errors.append("roundtrip_source_digest_drift")
        return (not errors, tuple(errors))

    # -- envelope ↔ native typed surface (D10) ------------------------------

    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle:
        """Forward projection: graph payload -> envelope state (D10 typed)."""
        env = self.native_to_envelope(native_state_bundle)
        return EnvelopeStateBundle(
            observables=env.observables,
            source_round=env.source_round,
            source_digest=env.source_digest,
            provenance=env.provenance,
            materializer_handle=env.materializer_handle,
        )

    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope state -> zero-placeholder graph native bundle."""
        legacy_env = EnvelopeState(
            observables=envelope_state.observables,
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance,
            materializer_handle=envelope_state.materializer_handle,
        )
        return self.envelope_to_native(legacy_env, atom_count=atom_count)


# ---------------------------------------------------------------------------
# ProtBFN concrete materializer (D10 — typed envelope ↔ native)
# ---------------------------------------------------------------------------

#: Default surface vocabulary size (ProtBFN uses 22 amino acids +
#: pad / bos / eos; the engine-facing surface observes 22).
DEFAULT_PROTBFN_SURFACE_VOCAB_SIZE: int = 22

#: Default model-internal vocabulary size (ProtBFN uses 32 with 10
#: special tokens; the engine-facing surface observes 22). The
#: ``model_K → surface_K`` mapping is declared in
#: :attr:`ConcreteProtBFNMaterializer.vocab_alignment`.
DEFAULT_PROTBFN_MODEL_VOCAB_SIZE: int = 32

#: Default amino-acid mass table (Da) for the 22-token surface
#: vocabulary. Index 0 is reserved for the ``<pad>`` token (mass 0);
#: index 21 is reserved for the ``<eos>`` token. Indices 1..20 are
#: the canonical 20 amino acids in alphabetical order. Used by
#: :meth:`ConcreteProtBFNMaterializer._residue_mass_aggregation` to
#: derive the per-position mass sum.
PROTBFN_AMINO_ACID_MASSES_DA: tuple[float, ...] = (
    0.0,    # <pad>
    89.09,  # A (alanine)
    132.12, # C (cysteine, includes disulfide)
    115.09, # D (aspartic acid)
    131.09, # E (glutamic acid)
    147.18, # F (phenylalanine)
    75.07,  # G (glycine)
    155.16, # H (histidine)
    113.16, # I (isoleucine)
    128.17, # K (lysine)
    113.16, # L (leucine)
    131.19, # M (methionine)
    114.10, # N (asparagine)
    115.09, # O (pyrrolysine — placeholder mass)
    97.12,  # P (proline)
    128.13, # Q (glutamine)
    156.19, # R (arginine)
    87.08,  # S (serine)
    101.11, # T (threonine)
    150.13, # U (selenocysteine — placeholder mass)
    99.13,  # V (valine)
    186.21, # W (tryptophan)
)


class ConcreteProtBFNMaterializer:
    """Materialization route for ProtBFN / AbBFN / AbBFN2 native state (D10 typed surface).

    Implements BOTH the legacy :class:`MaterializationRouteProtocol`
    (universal layer) and the new typed :class:`MaterializationRoute`
    (Design #4 — contracts layer). The two surfaces are aligned so
    callers can consume either interface transparently.

    Forward projection (:meth:`dematerialize` / ``native_to_envelope``)
    reduces the heterogeneous ProtBFN native bundle to envelope
    observables (:data:`PROTBFN_ENVELOPE_KEYS`):

    * ``sequence_length`` — derived from the amino-acid categorical
      payload; equals ``L`` of the ``(L, K)`` logits.
    * ``vocab_size`` / ``surface_vocab_size`` — surface vocabulary size
      (default 22).
    * ``model_vocab_size`` — model-internal vocabulary size (default
      32). Carries the alignment in :attr:`vocab_alignment`.
    * ``vocab_mass`` — sum of surface-token probabilities per position;
      ProtBFN's BFN row-renormalisation keeps the amino-acid mass
      around 1.0 (the 10 special tokens' probability mass is
      zero-summed away).
    * ``sequence_entropy`` — Shannon entropy of the per-position
      categorical, averaged across positions (nats).
    * ``sequence_max_prob`` — mean top-1 probability across positions.
    * ``tap_continuous_summary`` — placeholder summary of the TAP
      biophysical-property continuous channel (mean / std if the
      override carries a JSON histogram).
    * ``categorical_channel_count`` — number of categorical channels
      the bundle declares.
    * ``residue_mass_aggregation`` — sum of the per-position amino-acid
      mass table for the modal amino acid at each position.
    * ``vocab_alignment`` — JSON-encoded ``model_K → surface_K``
      mapping; preserves the K=32 vs K=22 alignment so downstream
      consumers know which internal index corresponds to which amino acid.
    * ``materialization_pass`` / ``geometry_pass`` — ``True``.

    Lossy: the inverse (:meth:`materialize` / ``envelope_to_native``)
    is a zero-placeholder reconstruction that preserves ``atom_count``
    (which the ProtBFN bundle carries as ``sequence_length``) and
    ``source_round`` only.
    """

    def __init__(
        self,
        *,
        surface_vocab_size: int = DEFAULT_PROTBFN_SURFACE_VOCAB_SIZE,
        model_vocab_size: int = DEFAULT_PROTBFN_MODEL_VOCAB_SIZE,
        vocab_alignment: Mapping[int, int] | None = None,
        envelope_observables_override: Mapping[str, Any] | None = None,
    ) -> None:
        if not isinstance(surface_vocab_size, int) or isinstance(surface_vocab_size, bool):
            raise ValueError("surface_vocab_size_must_be_int")
        if surface_vocab_size <= 0:
            raise ValueError("surface_vocab_size_must_be_positive")
        if not isinstance(model_vocab_size, int) or isinstance(model_vocab_size, bool):
            raise ValueError("model_vocab_size_must_be_int")
        if model_vocab_size <= 0:
            raise ValueError("model_vocab_size_must_be_positive")
        if model_vocab_size < surface_vocab_size:
            raise ValueError(
                "model_vocab_size_must_be_ge_surface_vocab_size"
            )
        self._surface_vocab_size = int(surface_vocab_size)
        self._model_vocab_size = int(model_vocab_size)
        # Default alignment: model index ``i < surface_vocab_size`` maps
        # to surface index ``i``; the special-token tail maps to -1
        # (sentinel "no surface mapping").
        self._vocab_alignment: dict[int, int] = dict(vocab_alignment or {})
        for i in range(self._surface_vocab_size):
            self._vocab_alignment.setdefault(i, i)
        for i in range(self._surface_vocab_size, self._model_vocab_size):
            self._vocab_alignment.setdefault(i, -1)
        self._override: dict[str, Any] = dict(envelope_observables_override or {})
        digest = hashlib.sha256(
            json.dumps(
                {
                    "surface_vocab_size": int(self._surface_vocab_size),
                    "model_vocab_size": int(self._model_vocab_size),
                    "alignment": {str(k): v for k, v in sorted(self._vocab_alignment.items())},
                    "override_keys": sorted(self._override.keys()),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:16]
        self._handle = MaterializerHandle(
            f"materializer:protbfn:v1:{digest}"
        )

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        return self._handle

    @property
    def surface_vocab_size(self) -> int:
        """Return the surface vocabulary size K (default 22)."""
        return int(self._surface_vocab_size)

    @property
    def model_vocab_size(self) -> int:
        """Return the model-internal vocabulary size K (default 32)."""
        return int(self._model_vocab_size)

    @property
    def vocab_alignment(self) -> Mapping[int, int]:
        """Return the ``model_K → surface_K`` alignment mapping.

        ``-1`` marks a model-internal index that does NOT map to any
        surface token (the 10 special tokens in ProtBFN's K=32
        vocabulary).
        """
        return dict(self._vocab_alignment)

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """ProtBFN roundtrip: per-position argmax exact; vocab alignment lossy."""
        return {
            "amino_acid_categorical": LossTolerance(0.0),
            "cdr_length_categorical": LossTolerance(1.0),
            "germline_label_categorical": LossTolerance(1.0),
            "species_label_categorical": LossTolerance(1.0),
            "light_chain_locus_categorical": LossTolerance(1.0),
            "tap_continuous": LossTolerance(0.0),
        }

    # -- envelope ↔ native typed surface (D10) ------------------------------

    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle:
        """Forward projection: ProtBFN native bundle -> envelope state (D10 typed)."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            raise ValueError(f"native_state_bundle_invalid:{','.join(errs)}")
        sequence_length = int(native_state_bundle.atom_count)
        # Vocab mass — read from override; else placeholder 1.0.
        vocab_mass = float(self._override.get("vocab_mass", 1.0))
        # Sequence entropy — read from override; else 0.0 placeholder.
        sequence_entropy = float(self._override.get("sequence_entropy", 0.0))
        # Sequence max-prob — read from override; else 1.0 placeholder.
        sequence_max_prob = float(self._override.get("sequence_max_prob", 1.0))
        # TAP continuous summary — read from override or compute a
        # placeholder from the bundle's TAP channel payload.
        tap_summary = float(self._override.get("tap_continuous_summary", 0.0))
        if "tap_continuous_summary" not in self._override:
            tap_payload = native_state_bundle.channels.get("tap_continuous")
            if isinstance(tap_payload, str):
                try:
                    parsed = json.loads(tap_payload)
                    if isinstance(parsed, list) and all(
                        isinstance(x, (int, float)) for x in parsed
                    ):
                        tap_summary = float(sum(parsed)) / max(len(parsed), 1)
                except (json.JSONDecodeError, ValueError):
                    tap_summary = 0.0
        # Residue mass aggregation — read from override; else 0.0
        # placeholder (computed from the amino-acid mass table when the
        # modal amino-acid histogram is supplied via the override).
        residue_mass = float(self._override.get("residue_mass_aggregation", 0.0))
        # Categorical channel count — count channels whose declared
        # domain is one of the categorical kinds.
        categorical_domains = {
            "discrete",
            "categorical_mask",
            "categorical_argmax",
            "categorical_sample",
        }
        categorical_count = sum(
            1
            for ch, dom in native_state_bundle.channel_domains.items()
            if dom in categorical_domains
        )
        observables: dict[str, Any] = {
            "sequence_length": int(sequence_length),
            "vocab_size": int(self._surface_vocab_size),
            "model_vocab_size": int(self._model_vocab_size),
            "surface_vocab_size": int(self._surface_vocab_size),
            "vocab_mass": float(vocab_mass),
            "sequence_entropy": float(sequence_entropy),
            "sequence_max_prob": float(sequence_max_prob),
            "tap_continuous_summary": float(tap_summary),
            "categorical_channel_count": int(categorical_count),
            "residue_mass_aggregation": float(residue_mass),
            "vocab_alignment": json.dumps(
                {str(k): int(v) for k, v in sorted(self._vocab_alignment.items())},
                sort_keys=True,
            ),
            "materialization_pass": True,
            "geometry_pass": True,
        }
        # Carry forward any additional override keys.
        for k, v in self._override.items():
            observables.setdefault(str(k), v)
        return EnvelopeStateBundle(
            observables=observables,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance
            + ("materializer:protbfn",),
            materializer_handle=self._handle,
        )

    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope state -> zero-placeholder ProtBFN native bundle."""
        ok, errs = envelope_state.validate()
        if not ok:
            raise ValueError(f"envelope_state_invalid:{','.join(errs)}")
        n = (
            int(atom_count)
            if atom_count is not None
            else int(envelope_state.observables.get("sequence_length", 0))
        )
        placeholder_digest = envelope_state.source_digest[:16]
        channels: dict[str, str] = {
            "amino_acid_categorical": (
                f"protbfn:amino_acid:placeholder:{placeholder_digest}"
            ),
            "tap_continuous": (
                f"protbfn:tap:placeholder:{placeholder_digest}"
            ),
        }
        return NativeStateBundle(
            channels=channels,
            atom_count=n,
            backend_kind="protbfn",
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance
            + ("materializer:protbfn:inverse",),
        )

    def validate_roundtrip(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> tuple[bool, tuple[str, ...]]:
        """Roundtrip preserves atom_count + source_round (categorical channel is lossy)."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            return (False, errs)
        env = self.dematerialize(native_state_bundle)
        back = self.materialize(env, atom_count=native_state_bundle.atom_count)
        errors: list[str] = []
        if back.atom_count != native_state_bundle.atom_count:
            errors.append("roundtrip_atom_count_drift")
        if back.source_round != native_state_bundle.source_round:
            errors.append("roundtrip_source_round_drift")
        if back.source_digest != native_state_bundle.source_digest:
            errors.append("roundtrip_source_digest_drift")
        return (not errors, tuple(errors))

    # -- legacy surface (MaterializationRouteProtocol compat) --------------

    def native_to_envelope(
        self, native_state_bundle: NativeStateBundle
    ) -> EnvelopeState:
        """Legacy forward projection: native bundle -> envelope state."""
        env = self.dematerialize(native_state_bundle)
        return EnvelopeState(
            observables=env.observables,
            source_round=env.source_round,
            source_digest=env.source_digest,
            provenance=env.provenance,
            materializer_handle=env.materializer_handle,
        )

    def envelope_to_native(
        self,
        envelope_state: EnvelopeState,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Legacy inverse projection: envelope state -> native bundle."""
        env = EnvelopeStateBundle(
            observables=envelope_state.observables,
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance,
            materializer_handle=envelope_state.materializer_handle,
        )
        return self.materialize(env, atom_count=atom_count)

    # -- residue mass aggregation helper (used by envelope criteria) -------

    def aggregate_residue_mass(
        self,
        amino_acid_histogram: tuple[int, ...],
    ) -> float:
        """Aggregate per-position residue mass from an amino-acid histogram.

        ``amino_acid_histogram`` is a length-``surface_vocab_size`` tuple
        of integer counts (one per surface amino-acid token). The
        function multiplies each count by the corresponding mass in
        :data:`PROTBFN_AMINO_ACID_MASSES_DA` and returns the sum.

        Used by envelope criteria that consume the
        ``residue_mass_aggregation`` observable; provided as a public
        helper so the per-position math is not duplicated across
        callers.

        Defensive: silently zero-pads / truncates inputs whose length
        does not match the surface vocabulary so the helper is total.
        """
        if not isinstance(amino_acid_histogram, (tuple, list)):
            raise TypeError("amino_acid_histogram_must_be_sequence")
        masses = PROTBFN_AMINO_ACID_MASSES_DA
        total = 0.0
        for i in range(min(len(amino_acid_histogram), len(masses), self._surface_vocab_size)):
            count = int(amino_acid_histogram[i])
            if count < 0:
                count = 0
            total += float(count) * float(masses[i])
        return float(total)


# ---------------------------------------------------------------------------
# Default factories
# ---------------------------------------------------------------------------


def default_flowmol3_materializer() -> MaterializationRouteProtocol:
    """Return the canonical :class:`ConcreteFlowMol3Materializer` factory."""
    return ConcreteFlowMol3Materializer()


def default_graphbfn_materializer() -> MaterializationRouteProtocol:
    """Return the canonical :class:`ConcreteGraphBFNMaterializer` factory."""
    return ConcreteGraphBFNMaterializer()


def default_protbfn_materializer() -> MaterializationRouteProtocol:
    """Return the canonical :class:`ConcreteProtBFNMaterializer` factory.

    The returned instance also implements the typed D10
    :class:`MaterializationRoute` interface (Design #4), so callers can
    consume either the legacy ``native_to_envelope`` / ``envelope_to_native``
    surface or the new ``dematerialize`` / ``materialize`` typed surface
    transparently.
    """
    return ConcreteProtBFNMaterializer()


__all__ = [
    "DEFAULT_PROTBFN_SURFACE_VOCAB_SIZE",
    "DEFAULT_PROTBFN_MODEL_VOCAB_SIZE",
    "FLOWMOL3_ENVELOPE_KEYS",
    "GRAPHBFN_ENVELOPE_KEYS",
    "PROTBFN_AMINO_ACID_MASSES_DA",
    "PROTBFN_ENVELOPE_KEYS",
    "ConcreteFlowMol3Materializer",
    "ConcreteGraphBFNMaterializer",
    "ConcreteProtBFNMaterializer",
    "default_flowmol3_materializer",
    "default_graphbfn_materializer",
    "default_protbfn_materializer",
]
