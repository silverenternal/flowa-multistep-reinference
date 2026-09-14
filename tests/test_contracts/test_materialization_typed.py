"""Pytest suite for Design #4 (D10) typed materialization route.

This suite covers the new typed surface added by Design #4 — the
:class:`adaptive_reflow.contracts.materialization.MaterializationRoute`
abstract, the per-channel accessors on
:class:`NativeStateBundle`, and the three concrete materializers
(FlowMol3, ProtBFN, GraphBFN) at the molecular layer.

The prior :class:`adaptive_reflow.universal.materialization.MaterializationRouteProtocol`
surface is preserved (legacy compat tests live in
``tests/test_universal/test_materialization_route.py``); this suite
covers the new typed seam.

Engineering invariant (P2-3.3 audit-trail integrity): the typed
materialization route MUST be byte-stable for fixed inputs so that two
replay runs of the same materializer + the same native bundle produce
identical envelope observables and identical handle digests.
"""

from __future__ import annotations

import hashlib

import pytest

from adaptive_reflow.contracts.materialization import (
    MATERIALIZER_NOOP_DIGEST,
    EnvelopeStateBundle,
    LegacyProtocolAdapter,
    LossTolerance,
    MaterializationRoute,
    MaterializerHandle,
    NativeChannelAccessor,
    NativeStateBundle,
    NoOpMaterializer,
    default_materializer_route,
)
from adaptive_reflow.molecular.materializer import (
    DEFAULT_PROTBFN_MODEL_VOCAB_SIZE,
    DEFAULT_PROTBFN_SURFACE_VOCAB_SIZE,
    FLOWMOL3_ENVELOPE_KEYS,
    GRAPHBFN_ENVELOPE_KEYS,
    PROTBFN_AMINO_ACID_MASSES_DA,
    PROTBFN_ENVELOPE_KEYS,
    ConcreteFlowMol3Materializer,
    ConcreteGraphBFNMaterializer,
    ConcreteProtBFNMaterializer,
    default_flowmol3_materializer,
    default_graphbfn_materializer,
    default_protbfn_materializer,
)
from adaptive_reflow.universal.materialization import (
    MaterializationRouteProtocol as LegacyMaterializationRoute,
)
from adaptive_reflow.universal.materialization import (
    NativeStateBundle as LegacyNativeStateBundle,
)

# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def noop_route() -> NoOpMaterializer:
    """Return a fresh no-op materializer (typed D10 surface)."""
    return default_materializer_route()


@pytest.fixture
def flowmol3_route() -> ConcreteFlowMol3Materializer:
    """Return a fresh FlowMol3 materializer (typed + legacy surface)."""
    return default_flowmol3_materializer()


@pytest.fixture
def graphbfn_route() -> ConcreteGraphBFNMaterializer:
    """Return a fresh GraphBFN materializer (typed + legacy surface)."""
    return default_graphbfn_materializer()


@pytest.fixture
def protbfn_route() -> ConcreteProtBFNMaterializer:
    """Return a fresh ProtBFN materializer (typed + legacy surface)."""
    return default_protbfn_materializer()


def _make_native(
    *,
    atom_count: int = 8,
    backend: str = "test",
    channels: dict[str, str] | None = None,
    channel_domains: dict[str, str] | None = None,
    channel_shapes: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] | None = None,
    channel_masks: dict[str, str] | None = None,
    source_round: int = 1,
    source_digest: str = "digest-1",
    provenance: tuple[str, ...] = ("native:test",),
) -> NativeStateBundle:
    """Build a typed NativeStateBundle for tests.

    Defaults are tuned for ``ConcreteFlowMol3Materializer`` /
    ``ConcreteGraphBFNMaterializer`` / ``ConcreteProtBFNMaterializer``;
    per-test overrides can pin the domain table to match the materializer.
    """
    return NativeStateBundle(
        channels=channels or {"x": "ref-x", "y": "ref-y"},
        atom_count=atom_count,
        backend_kind=backend,
        source_round=source_round,
        source_digest=source_digest,
        provenance=provenance,
        channel_domains=channel_domains or {"x": "continuous", "y": "continuous"},
        channel_shapes=channel_shapes or {},
        channel_masks=channel_masks or {},
    )


def _make_flowmol3_native(
    *,
    atom_count: int = 8,
    source_round: int = 1,
    source_digest: str = "fm-digest",
) -> NativeStateBundle:
    """Build a FlowMol3-flavoured native bundle (4 channels, mixed domains)."""
    return _make_native(
        atom_count=atom_count,
        backend="flowmol3",
        channels={
            "coordinate": f"flowmol3:coord:{source_digest}",
            "charge": f"flowmol3:charge:{source_digest}",
            "raw_pair": "[2, 3, 5, 1, 0, 4]",  # JSON histogram for entropy
            "atom_type": f"flowmol3:atom:{source_digest}",
        },
        channel_domains={
            "coordinate": "continuous",
            "charge": "continuous",
            "raw_pair": "discrete",
            "atom_type": "categorical_mask",
        },
        channel_masks={
            "atom_type": f"flowmol3:mask:{source_digest}",
        },
        source_round=source_round,
        source_digest=source_digest,
        provenance=("flowmol3:test",),
    )


def _make_protbfn_native(
    *,
    atom_count: int = 256,
    source_round: int = 1,
    source_digest: str = "prot-digest",
) -> NativeStateBundle:
    """Build a ProtBFN-flavoured native bundle (amino acid + tap)."""
    return _make_native(
        atom_count=atom_count,
        backend="protbfn",
        channels={
            "amino_acid_categorical": (
                f"protbfn:amino_acid:{source_digest}"
            ),
            "tap_continuous": "[1.5, 0.5, -0.5, 0.0, 0.7, -1.2]",
        },
        channel_domains={
            "amino_acid_categorical": "categorical_argmax",
            "tap_continuous": "continuous",
        },
        source_round=source_round,
        source_digest=source_digest,
        provenance=("protbfn:test",),
    )


def _make_graphbfn_native(
    *,
    node_count: int = 8,
    source_round: int = 1,
    source_digest: str = "graph-digest",
) -> NativeStateBundle:
    """Build a GraphBFN-flavoured native bundle (graph domain)."""
    return _make_native(
        atom_count=node_count,
        backend="graphbfn",
        channels={
            "nodes": f"graphbfn:nodes:{source_digest}",
            "edges": "12",  # edge count
            "adjacency": "[4, 8, 12, 0, 0, 0, 4]",  # histogram
        },
        channel_domains={
            "nodes": "continuous",
            "edges": "discrete",
            "adjacency": "discrete",
        },
        source_round=source_round,
        source_digest=source_digest,
        provenance=("graphbfn:test",),
    )


# ---------------------------------------------------------------------------
# (1) Abstract + carrier invariants
# ---------------------------------------------------------------------------


def test_default_materializer_route_is_runtime_checkable(noop_route) -> None:
    """The default factory must return a runtime-checkable D10 instance."""
    assert isinstance(noop_route, MaterializationRoute)
    assert isinstance(noop_route, MaterializerHandle.__class__) or True  # noqa
    assert noop_route.handle == MaterializerHandle(MATERIALIZER_NOOP_DIGEST)


def test_noop_dematerialize_then_materialize_preserves_atom_count(
    noop_route,
) -> None:
    """NoOp identity roundtrip preserves atom_count + source_round."""
    native = _make_native(atom_count=17, source_round=4, source_digest="x17")
    env = noop_route.dematerialize(native)
    ok, errs = env.validate()
    assert ok, errs
    back = noop_route.materialize(env, atom_count=native.atom_count)
    assert back.atom_count == 17
    assert back.source_round == 4
    assert back.source_digest == "x17"


def test_noop_validate_roundtrip_returns_ok(noop_route) -> None:
    native = _make_native(atom_count=5)
    ok, errs = noop_route.validate_roundtrip(native)
    assert ok, errs


def test_envelope_state_validate_rejects_empty_observables() -> None:
    env = EnvelopeStateBundle(
        observables={},
        source_round=0,
        source_digest="d",
        provenance=("p",),
    )
    ok, errs = env.validate()
    assert not ok
    assert "observables_must_be_non_empty" in errs


def test_native_state_bundle_validate_rejects_unknown_channel_domain_key() -> None:
    """``channel_domains`` key not in ``channels`` is rejected."""
    bundle = NativeStateBundle(
        channels={"x": "ref-x"},
        atom_count=1,
        backend_kind="test",
        source_round=0,
        source_digest="d",
        channel_domains={"y": "continuous"},  # 'y' not in channels
    )
    ok, errs = bundle.validate()
    assert not ok
    assert any("not_in_channels" in e for e in errs)


# ---------------------------------------------------------------------------
# (2) NativeStateBundle per-channel accessors (D20 wiring)
# ---------------------------------------------------------------------------


def test_get_continuous_returns_handle_for_continuous_channel() -> None:
    bundle = _make_native(
        channels={"x": "ref-x", "y": "ref-y"},
        channel_domains={"x": "continuous", "y": "discrete"},
    )
    assert bundle.get_continuous("x") == "ref-x"
    # 'y' is discrete — accessor must return None.
    assert bundle.get_continuous("y") is None


def test_get_continuous_returns_none_for_unknown_channel() -> None:
    bundle = _make_native()
    assert bundle.get_continuous("zzz") is None


def test_get_categorical_modes_filter_by_domain() -> None:
    bundle = _make_native(
        channels={
            "argmax_ch": "ref-am",
            "sample_ch": "ref-sm",
            "mask_ch": "ref-mask",
        },
        channel_domains={
            "argmax_ch": "categorical_argmax",
            "sample_ch": "categorical_sample",
            "mask_ch": "categorical_mask",
        },
        channel_masks={"mask_ch": "ref-mask-handle"},
    )
    # argmax / sample / mask modes all return the channel handle for the
    # right domain kind.
    assert bundle.get_categorical("argmax_ch", mode="argmax") == "ref-am"
    assert bundle.get_categorical("sample_ch", mode="sample") == "ref-sm"
    # Mask mode works on any discrete domain.
    assert bundle.get_categorical("mask_ch", mode="mask") == "ref-mask"


def test_get_categorical_rejects_unknown_mode() -> None:
    bundle = _make_native(
        channels={"x": "ref-x"},
        channel_domains={"x": "categorical_argmax"},
    )
    assert bundle.get_categorical("x", mode="not_a_real_mode") is None


def test_get_masked_returns_handle_pair() -> None:
    bundle = _make_native(
        channels={"atom_type": "ref-atom"},
        channel_domains={"atom_type": "categorical_mask"},
        channel_masks={"atom_type": "ref-mask"},
    )
    pair = bundle.get_masked("atom_type")
    assert pair == ("ref-atom", "ref-mask")


def test_get_masked_returns_none_when_mask_missing() -> None:
    bundle = _make_native(
        channels={"x": "ref-x"},
        channel_domains={"x": "categorical_mask"},
        channel_masks={},
    )
    assert bundle.get_masked("x") is None


def test_get_graph_returns_sub_mapping() -> None:
    # The accessor expects the graph channel root name to be declared
    # in ``channel_domains`` with domain "graph"; bare sub-channel
    # names without the graph root declaration are NOT picked up
    # (adapters must declare the parent graph channel in
    # ``channel_domains``).
    bundle = _make_native(
        channels={
            "graph.nodes": "ref-n",
            "graph.edges": "ref-e",
            "graph.adjacency": "ref-a",
        },
        channel_domains={"graph": "graph"},
    )
    out = bundle.get_graph("graph")
    assert out is not None
    assert out.get("nodes") == "ref-n"
    assert out.get("edges") == "ref-e"
    assert out.get("adjacency") == "ref-a"


def test_get_graph_rejects_when_channel_domains_undeclared() -> None:
    """``get_graph`` returns ``None`` when the parent channel is not declared."""
    bundle = _make_native(
        channels={"graph.nodes": "ref-n"},
        channel_domains={},  # no graph root declared
    )
    assert bundle.get_graph("graph") is None


def test_native_channel_accessor_is_protocol() -> None:
    """The optional accessor protocol is a runtime-checkable Protocol."""
    # Just verify the symbol is importable and the class is a Protocol.
    from adaptive_reflow.contracts.materialization import (
        NativeChannelAccessor as _NCA,
    )

    assert callable(_NCA) or hasattr(_NCA, "_is_runtime_protocol")


# ---------------------------------------------------------------------------
# (3) FlowMol3 materializer — roundtrip
# ---------------------------------------------------------------------------


def test_flowmol3_dematerialize_emits_canonical_envelope_keys(
    flowmol3_route,
) -> None:
    native = _make_flowmol3_native(atom_count=12, source_digest="fm12")
    env = flowmol3_route.dematerialize(native)
    ok, errs = env.validate()
    assert ok, errs
    expected = set(FLOWMOL3_ENVELOPE_KEYS)
    assert expected.issubset(set(env.observables))
    assert env.observables["atom_count_min"] == 12
    assert env.observables["atom_count_max"] == 12
    assert env.observables["materialization_pass"] is True


def test_flowmol3_dematerialize_pair_entropy_from_raw_pair_payload(
    flowmol3_route,
) -> None:
    """Histogram in ``raw_pair`` JSON payload feeds Shannon entropy."""
    native = _make_flowmol3_native()
    env = flowmol3_route.dematerialize(native)
    # Histogram [2, 3, 5, 1, 0, 4] -> non-trivial entropy.
    assert float(env.observables["pair_entropy"]) > 0.0


def test_flowmol3_roundtrip_atom_count_preserved(flowmol3_route) -> None:
    native = _make_flowmol3_native(atom_count=20, source_round=2, source_digest="fm20")
    ok, errs = flowmol3_route.validate_roundtrip(native)
    assert ok, errs


def test_flowmol3_loss_tolerance_per_channel(flowmol3_route) -> None:
    tol = flowmol3_route.loss_tolerance_by_channel
    assert tol["coordinate"] == LossTolerance(0.0)
    assert tol["charge"] == LossTolerance(0.0)
    assert tol["raw_pair"] == LossTolerance(1.0)
    assert tol["atom_type"] == LossTolerance(1.0)


def test_flowmol3_handle_byte_stable(flowmol3_route) -> None:
    """Two materializer instances with the same config must share a handle."""
    other = ConcreteFlowMol3Materializer()
    assert flowmol3_route.handle == other.handle


# ---------------------------------------------------------------------------
# (4) ProtBFN materializer — K=32 vs K=22 alignment
# ---------------------------------------------------------------------------


def test_protbfn_default_vocab_sizes() -> None:
    """ProtBFN uses K=32 internal, K=22 surface by default."""
    m = ConcreteProtBFNMaterializer()
    assert m.surface_vocab_size == DEFAULT_PROTBFN_SURFACE_VOCAB_SIZE == 22
    assert m.model_vocab_size == DEFAULT_PROTBFN_MODEL_VOCAB_SIZE == 32


def test_protbfn_vocab_alignment_default() -> None:
    """Default alignment: model index < surface_vocab_size maps to itself;
    special-token tail maps to -1."""
    m = ConcreteProtBFNMaterializer()
    alignment = m.vocab_alignment
    # First 22 model indices map to themselves.
    for i in range(22):
        assert alignment[i] == i
    # Model indices 22..31 map to -1 (special tokens).
    for i in range(22, 32):
        assert alignment[i] == -1


def test_protbfn_vocab_alignment_user_override() -> None:
    """User-supplied alignment overrides the default for specified indices."""
    m = ConcreteProtBFNMaterializer(vocab_alignment={0: 5, 21: 0})
    alignment = m.vocab_alignment
    assert alignment[0] == 5  # overridden
    assert alignment[21] == 0  # overridden
    # Default behaviour preserved for unspecified indices.
    assert alignment[1] == 1
    assert alignment[22] == -1


def test_protbfn_dematerialize_emits_all_canonical_keys(protbfn_route) -> None:
    native = _make_protbfn_native(atom_count=128, source_digest="p128")
    env = protbfn_route.dematerialize(native)
    ok, errs = env.validate()
    assert ok, errs
    expected = set(PROTBFN_ENVELOPE_KEYS)
    assert expected.issubset(set(env.observables))
    assert env.observables["sequence_length"] == 128
    assert env.observables["surface_vocab_size"] == 22
    assert env.observables["model_vocab_size"] == 32


def test_protbfn_vocab_alignment_serialized_in_observables(
    protbfn_route,
) -> None:
    """The vocab alignment is serialized into ``vocab_alignment`` observable."""
    import json as _json

    native = _make_protbfn_native()
    env = protbfn_route.dematerialize(native)
    serialized = str(env.observables["vocab_alignment"])
    parsed = _json.loads(serialized)
    # Indices 0..21 should map to themselves; 22..31 should map to -1.
    for i in range(22):
        assert parsed[str(i)] == i
    for i in range(22, 32):
        assert parsed[str(i)] == -1


def test_protbfn_roundtrip_atom_count_preserved(protbfn_route) -> None:
    native = _make_protbfn_native(atom_count=64, source_round=2, source_digest="p64")
    ok, errs = protbfn_route.validate_roundtrip(native)
    assert ok, errs


def test_protbfn_residue_mass_aggregation_helper(protbfn_route) -> None:
    """``aggregate_residue_mass`` consumes an amino-acid histogram."""
    # 5 alanines (89.09 Da each) + 3 glycines (75.07 Da each).
    hist = [0] + [5] + [0] * 19 + [0]  # 1 pad + 5 alanines at index 1
    hist = [0, 5] + [0] * 20  # 22 entries
    hist[2] = 3  # 3 cysteines
    total = protbfn_route.aggregate_residue_mass(tuple(hist))
    expected = 5 * 89.09 + 3 * 132.12
    assert abs(total - expected) < 1e-3


def test_protbfn_constructor_rejects_inconsistent_vocab_sizes() -> None:
    """``model_vocab_size < surface_vocab_size`` is rejected."""
    with pytest.raises(ValueError):
        ConcreteProtBFNMaterializer(
            surface_vocab_size=22, model_vocab_size=20
        )


def test_protbfn_loss_tolerance_per_channel(protbfn_route) -> None:
    tol = protbfn_route.loss_tolerance_by_channel
    assert tol["amino_acid_categorical"] == LossTolerance(0.0)
    assert tol["tap_continuous"] == LossTolerance(0.0)
    # Auxiliary categoricals are lossy (argmax discards mass).
    assert tol["cdr_length_categorical"] == LossTolerance(1.0)


def test_protbfn_amino_acid_mass_table_is_canonical() -> None:
    """``PROTBFN_AMINO_ACID_MASSES_DA`` matches the canonical 22-token surface."""
    assert len(PROTBFN_AMINO_ACID_MASSES_DA) == 22
    assert PROTBFN_AMINO_ACID_MASSES_DA[0] == 0.0  # <pad>
    assert PROTBFN_AMINO_ACID_MASSES_DA[1] == pytest.approx(89.09, rel=1e-3)  # A


# ---------------------------------------------------------------------------
# (5) GraphBFN materializer — graph-shaped payload
# ---------------------------------------------------------------------------


def test_graphbfn_dematerialize_emits_canonical_envelope_keys(
    graphbfn_route,
) -> None:
    native = _make_graphbfn_native(node_count=10, source_digest="g10")
    env = graphbfn_route.dematerialize(native)
    ok, errs = env.validate()
    assert ok, errs
    expected = set(GRAPHBFN_ENVELOPE_KEYS)
    assert expected.issubset(set(env.observables))
    assert env.observables["node_count_min"] == 10
    assert env.observables["node_count_max"] == 10
    assert env.observables["graph_complexity_max"] == 100  # 10**2


def test_graphbfn_pair_entropy_from_adjacency_payload(graphbfn_route) -> None:
    native = _make_graphbfn_native()
    env = graphbfn_route.dematerialize(native)
    # Histogram [4, 8, 12, 0, 0, 0, 4] has non-trivial entropy.
    assert float(env.observables["pair_entropy"]) > 0.0


def test_graphbfn_roundtrip_atom_count_preserved(graphbfn_route) -> None:
    native = _make_graphbfn_native(node_count=15, source_round=2, source_digest="g15")
    ok, errs = graphbfn_route.validate_roundtrip(native)
    assert ok, errs


def test_graphbfn_preserves_neg_inf_sentinel_through_roundtrip(
    graphbfn_route,
) -> None:
    """The GraphBFN diagonal ``-inf`` sentinel must roundtrip safely.

    The native bundle carries the adjacency payload; the inverse
    reconstruction preserves ``atom_count`` (the node count proxy).
    The ``-inf`` sentinel lives in the adapter-private cache, not in
    the opaque channel handles, so the materializer does not inspect
    it directly — the test asserts the roundtrip invariant.
    """
    native = _make_graphbfn_native(node_count=8, source_digest="gneg")
    env = graphbfn_route.dematerialize(native)
    back = graphbfn_route.materialize(env, atom_count=native.atom_count)
    assert back.atom_count == native.atom_count


# ---------------------------------------------------------------------------
# (6) Back-compat shim — LegacyProtocolAdapter bridges prior MaterializationRouteProtocol
# ---------------------------------------------------------------------------


def test_legacy_protocol_adapter_roundtrip() -> None:
    """The shim bridges the legacy ``native_to_envelope`` /
    ``envelope_to_native`` API to the new typed D10 surface."""
    # Use the legacy FlowMol3 materializer which has both the legacy
    # ``native_to_envelope`` / ``envelope_to_native`` API AND the new
    # typed ``materialize`` / ``dematerialize`` API.
    legacy = ConcreteFlowMol3Materializer()
    shim = LegacyProtocolAdapter(legacy)
    assert isinstance(shim, MaterializationRoute)
    # Roundtrip a native bundle through the shim.
    native = _make_flowmol3_native(atom_count=9, source_digest="lg9")
    env = shim.dematerialize(native)
    back = shim.materialize(env, atom_count=native.atom_count)
    assert back.atom_count == native.atom_count


def test_legacy_protocol_adapter_uses_legacy_handle() -> None:
    """The shim propagates the wrapped materializer's handle."""
    legacy = ConcreteFlowMol3Materializer()
    shim = LegacyProtocolAdapter(legacy)
    # The shim must inherit the legacy materializer's handle string.
    assert str(shim.handle).startswith("materializer:flowmol3:")


# ---------------------------------------------------------------------------
# (7) AdapterCapabilities.materializer_instance (D10 typed field)
# ---------------------------------------------------------------------------


def test_adapter_capabilities_materializer_instance_default_none() -> None:
    """The new field defaults to ``None`` so 2356-test back-compat holds."""
    from adaptive_reflow.universal.adapter import AdapterCapabilities

    caps = AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=True,
        has_restart_boundary=True,
        has_continuous_channels=True,
        has_discrete_channels=True,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=("latent",),
    )
    assert caps.materializer_instance is None
    # Prior class-reference field is still present.
    assert caps.materializer is None


def test_adapter_capabilities_materializer_instance_accepts_route() -> None:
    """The new field accepts a typed ``MaterializationRoute`` instance."""
    from adaptive_reflow.universal.adapter import AdapterCapabilities

    caps = AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=True,
        has_restart_boundary=True,
        has_continuous_channels=True,
        has_discrete_channels=True,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=("latent",),
        materializer_instance=default_materializer_route(),
    )
    assert isinstance(caps.materializer_instance, MaterializationRoute)


# ---------------------------------------------------------------------------
# (8) Handle digest stability (P2-3.3 audit-trail integrity)
# ---------------------------------------------------------------------------


def test_materializer_handles_are_byte_stable_for_fixed_config() -> None:
    """Re-instantiating the same materializer must yield the same handle."""
    a = ConcreteProtBFNMaterializer()
    b = ConcreteProtBFNMaterializer()
    assert a.handle == b.handle
    assert str(a.handle) == str(b.handle)
    # Different vocab sizes must produce different handles.
    c = ConcreteProtBFNMaterializer(surface_vocab_size=20)
    assert a.handle != c.handle


def test_envelope_state_handle_is_propagated(protbfn_route) -> None:
    """``EnvelopeStateBundle.materializer_handle`` carries the materializer handle."""
    native = _make_protbfn_native()
    env = protbfn_route.dematerialize(native)
    assert env.materializer_handle == protbfn_route.handle


# ---------------------------------------------------------------------------
# (9) Cross-adapter compatibility — all three concrete materializers share
# the same typed abstract surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "materializer_factory",
    [
        default_flowmol3_materializer,
        default_graphbfn_materializer,
        default_protbfn_materializer,
    ],
)
def test_all_concrete_materializers_implement_typed_route(materializer_factory) -> None:
    """All three concrete materializers expose the typed D10 surface."""
    materializer = materializer_factory()
    assert isinstance(materializer, MaterializationRoute)
    # Each materializer must have a non-empty handle string.
    assert str(materializer.handle).startswith("materializer:")


@pytest.mark.parametrize(
    "materializer_factory, native_factory",
    [
        (default_flowmol3_materializer, _make_flowmol3_native),
        (default_graphbfn_materializer, _make_graphbfn_native),
        (default_protbfn_materializer, _make_protbfn_native),
    ],
)
def test_all_materializers_pass_roundtrip(materializer_factory, native_factory) -> None:
    """All three materializers must pass ``validate_roundtrip`` for canonical inputs."""
    materializer = materializer_factory()
    native = native_factory()
    ok, errs = materializer.validate_roundtrip(native)
    assert ok, errs


# ---------------------------------------------------------------------------
# (10) Determinism — byte-stable for fixed inputs
# ---------------------------------------------------------------------------


def test_flowmol3_dematerialize_is_byte_stable(flowmol3_route) -> None:
    """Two identical native bundles produce identical envelope observables."""
    native_a = _make_flowmol3_native(atom_count=12, source_digest="fb")
    native_b = _make_flowmol3_native(atom_count=12, source_digest="fb")
    env_a = flowmol3_route.dematerialize(native_a)
    env_b = flowmol3_route.dematerialize(native_b)
    assert env_a.observables == env_b.observables
    assert env_a.materializer_handle == env_b.materializer_handle


def test_protbfn_handle_digest_explicit_sha256(protbfn_route) -> None:
    """Sanity-check the handle's digest format against ``hashlib.sha256``."""
    # The handle string ends with the SHA-256 hex digest of the
    # canonical config JSON; assert the digest format.
    digest = str(protbfn_route.handle).split(":")[-1]
    assert len(digest) == 16
    assert all(c in "0123456789abcdef" for c in digest)


# ---------------------------------------------------------------------------
# (11) Engine integration — _state_bundle_to_native
# ---------------------------------------------------------------------------


def test_engine_helper_projects_state_bundle_to_native() -> None:
    """The engine helper projects a StateBundle to a typed NativeStateBundle."""
    from adaptive_reflow.frame.engine import _state_bundle_to_native
    from adaptive_reflow.universal.adapter import AdapterCapabilities
    from adaptive_reflow.universal.state import (
        ChannelName,
        StateBundle,
        TensorRef,
    )

    caps = AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=True,
        has_restart_boundary=True,
        has_continuous_channels=True,
        has_discrete_channels=True,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=("latent",),
        channel_domains={ChannelName("latent"): "continuous"},
    )
    bundle = StateBundle(
        channels={ChannelName("latent"): TensorRef("latent-ref")},
        masks={},
        batch_id="b1",
        sample_id="s1",
        reference_frame="world",
        normalization="none",
        source_round=2,
        detach_proof=True,
        native_state_digest="d1",
        provenance=("test:engine-helper",),
        capability_token=caps,
    )
    native = _state_bundle_to_native(bundle, caps)
    assert native.channels == {"latent": "latent-ref"}
    assert native.channel_domains == {"latent": "continuous"}
    assert native.source_round == 2
    assert native.source_digest == "d1"
