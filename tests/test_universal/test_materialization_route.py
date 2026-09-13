"""Pytest suite for :mod:`adaptive_reflow.universal.materialization` (D2 — materialization route)."""

from __future__ import annotations

import pytest

from adaptive_reflow.universal.materialization import (
    MATERIALIZER_NOOP_DIGEST,
    EnvelopeState,
    HeterogeneousCategoricalMaterializer,
    MaterializationRouteProtocol,
    MaterializerHandle,
    NativeStateBundle,
    NoOpMaterializer,
    default_materializer,
)

# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def noop() -> NoOpMaterializer:
    return NoOpMaterializer()


@pytest.fixture
def cat_materializer() -> HeterogeneousCategoricalMaterializer:
    return HeterogeneousCategoricalMaterializer(vocab_size=4)


def _make_native(
    *,
    atom_count: int = 8,
    backend: str = "test",
    channels: dict[str, str] | None = None,
    source_round: int = 1,
    source_digest: str = "digest-1",
) -> NativeStateBundle:
    return NativeStateBundle(
        channels=channels or {"x": "ref-x", "y": "ref-y"},
        atom_count=atom_count,
        backend_kind=backend,
        source_round=source_round,
        source_digest=source_digest,
    )


# ---------------------------------------------------------------------------
# (1) NoOpMaterializer is identity.
# ---------------------------------------------------------------------------


def test_noop_roundtrip_preserves_atom_count(noop) -> None:
    native = _make_native(atom_count=12, source_round=3, source_digest="d12")
    env = noop.native_to_envelope(native)
    ok, errs = env.validate()
    assert ok, errs
    back = noop.envelope_to_native(env, atom_count=native.atom_count)
    ok2, errs2 = noop.validate_roundtrip(native)
    assert ok2, errs2
    assert back.atom_count == native.atom_count


def test_noop_emits_canonical_handle(noop) -> None:
    assert noop.handle == MaterializerHandle(MATERIALIZER_NOOP_DIGEST)


# ---------------------------------------------------------------------------
# (2) HeterogeneousCategoricalMaterializer.
# ---------------------------------------------------------------------------


def test_categorical_materializer_vocab_size_required() -> None:
    with pytest.raises(ValueError):
        HeterogeneousCategoricalMaterializer(vocab_size=0)
    with pytest.raises(ValueError):
        HeterogeneousCategoricalMaterializer(vocab_size=-1)


def test_categorical_materializer_emits_envelope(cat_materializer) -> None:
    native = _make_native(atom_count=6, backend="test_cat")
    env = cat_materializer.native_to_envelope(native)
    assert env.observables["vocab_size"] == 4
    assert env.observables["atom_count"] == 6
    assert env.observables["backend_kind"] == "test_cat"
    assert env.observables["categorical_loss_tolerance"] == 1.0


def test_categorical_materializer_roundtrip_lossy(
    cat_materializer,
) -> None:
    native = _make_native(atom_count=7, source_round=4, source_digest="d7")
    ok, errs = cat_materializer.validate_roundtrip(native)
    assert ok, errs


def test_categorical_loss_tolerance_is_one(cat_materializer) -> None:
    assert cat_materializer.loss_tolerance_by_channel["categorical"] == 1.0


# ---------------------------------------------------------------------------
# (3) EnvelopeState + NativeStateBundle validators.
# ---------------------------------------------------------------------------


def test_envelope_state_rejects_empty_observables() -> None:
    bad = EnvelopeState(
        observables={},
        source_round=0,
        source_digest="x",
        provenance=("test",),
    )
    ok, errs = bad.validate()
    assert not ok
    assert any("observables" in e for e in errs)


def test_envelope_state_rejects_negative_source_round() -> None:
    bad = EnvelopeState(
        observables={"x": 1.0},
        source_round=-1,
        source_digest="x",
        provenance=("test",),
    )
    ok, errs = bad.validate()
    assert not ok
    assert any("source_round" in e for e in errs)


def test_native_bundle_rejects_empty_channels() -> None:
    bad = NativeStateBundle(
        channels={},
        atom_count=0,
        backend_kind="x",
        source_round=0,
        source_digest="x",
    )
    ok, errs = bad.validate()
    assert not ok
    assert any("channels" in e for e in errs)


def test_native_bundle_rejects_negative_atom_count() -> None:
    bad = NativeStateBundle(
        channels={"x": "y"},
        atom_count=-1,
        backend_kind="x",
        source_round=0,
        source_digest="x",
    )
    ok, errs = bad.validate()
    assert not ok
    assert any("atom_count" in e for e in errs)


# ---------------------------------------------------------------------------
# (4) Protocol conformance (runtime_checkable).
# ---------------------------------------------------------------------------


def test_noop_satisfies_protocol(noop) -> None:
    assert isinstance(noop, MaterializationRouteProtocol)


def test_categorical_satisfies_protocol(cat_materializer) -> None:
    assert isinstance(cat_materializer, MaterializationRouteProtocol)


def test_default_factory_returns_noop() -> None:
    m = default_materializer()
    assert isinstance(m, NoOpMaterializer)
    assert isinstance(m, MaterializationRouteProtocol)
