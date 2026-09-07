"""Wave 68 Phase 1: AdapterObservationProtocol contract tests.

Confirms the structural-typing contract of
:class:`adaptive_reflow.framework.interfaces.AdapterObservationProtocol`:

* :class:`ObservationKind` enum has the four Wave 67 §4 tags and is
  ``str``-mixin (JSON-serialisable).
* :class:`ObservationResult` is a frozen dataclass with the documented
  fields and a default empty ``metadata``.
* :class:`AdapterObservationProtocol` is ``@runtime_checkable``: classes
  declaring the ``observe(...)`` method pass ``isinstance``; classes
  without the method fail.
* :func:`implements` + :func:`assert_adapter_compliance` enforce the
  Protocol at import time.
* The default ``strategies`` tuple requests all four
  :class:`ObservationKind` values (Wave 68 §4 contract).
"""
from __future__ import annotations

import dataclasses
import json

import pytest

from adaptive_reflow.framework.interfaces import (
    AdapterObservationProtocol,
    MissingProtocolError,
    ObservationKind,
    ObservationResult,
    assert_adapter_compliance,
    implements,
)


# --- Adapters below are minimal fixtures, not real adapters ---


@implements(AdapterObservationProtocol)
class MockObserverAll:
    """Compliant observer returning all four strategies."""

    def observe(self, trace, state, paper_quantities=None, *, strategies=..., theta_before=None, theta_after=None):
        # Accept any strategies tuple, return one result per kind.
        return tuple(
            ObservationResult(
                kind=k,
                channel="mock",
                payload={"trace": trace, "state": state},
                units="unitless",
                metadata={"theta_after": theta_after, "theta_before": theta_before},
            )
            for k in ObservationKind
        )


@implements(AdapterObservationProtocol)
class MockObserverEmpty:
    """Compliant observer returning an empty tuple (synthetic / ref adapter)."""

    def observe(self, trace, state, paper_quantities=None, *, strategies=..., theta_before=None, theta_after=None):
        return ()


@implements(AdapterObservationProtocol)
class MockObserverPartial:
    """Compliant observer returning only DISCRETE_TOKENS (Kanzi-like)."""

    def observe(self, trace, state, paper_quantities=None, *, strategies=..., theta_before=None, theta_after=None):
        return (
            ObservationResult(
                kind=ObservationKind.DISCRETE_TOKENS,
                channel="discrete_idx",
                payload=[0, 1, 2, 3],
                units="indices",
            ),
        )


class NonCompliantObserver:
    """No ``observe`` method at all."""


@implements(AdapterObservationProtocol)
class DeclaredButMissingObserver(NonCompliantObserver):
    """Declares conformance but does NOT implement ``observe``.

    Distinct from :class:`NonCompliantObserver` (which is silent under
    :func:`assert_adapter_compliance` because it never declared the
    Protocol). This class declares conformance and therefore MUST raise
    :class:`MissingProtocolError` on enforcement.
    """


# --- ObservationKind ---


def test_observation_kind_has_four_tags():
    """Wave 67 §4: four kinds cover every existing observation method."""
    expected = {
        "ENDPOINT_BUNDLE",
        "DISCRETE_TOKENS",
        "POSITION_ENTROPY_REDUCTION",
        "TRAJECTORY_NATIVE",
    }
    assert {k.name for k in ObservationKind} == expected


def test_observation_kind_values_are_snake_case_strings():
    """The ``str`` mixin lets the enum round-trip through ``json.dumps``."""
    for k in ObservationKind:
        assert isinstance(k.value, str)
        assert k.value == k.value.lower()
        # str-mixin: k behaves as a plain str.
        assert k == k.value
    # JSON-serialisable without a custom encoder.
    encoded = json.dumps([k.value for k in ObservationKind])
    decoded = json.loads(encoded)
    assert decoded == [k.value for k in ObservationKind]


# --- ObservationResult dataclass ---


def test_observation_result_is_frozen():
    """Frozen dataclass -- immutable after construction (Wave 11 pattern)."""
    r = ObservationResult(
        kind=ObservationKind.ENDPOINT_BUNDLE,
        channel="atom_type",
        payload=0.5,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.channel = "mutated"  # type: ignore[misc]


def test_observation_result_default_metadata_is_empty_mapping():
    """``metadata`` defaults to ``{}`` and is per-instance (no shared state)."""
    r1 = ObservationResult(kind=ObservationKind.ENDPOINT_BUNDLE, channel="x", payload=1)
    r2 = ObservationResult(kind=ObservationKind.ENDPOINT_BUNDLE, channel="y", payload=2)
    assert r1.metadata == {}
    assert r2.metadata == {}
    # Per-instance dict (mutable default trap avoided).
    assert r1.metadata is not r2.metadata


def test_observation_result_carries_units_and_metadata():
    """``units`` and ``metadata`` are surfaced for the metric layer."""
    r = ObservationResult(
        kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        channel="atom_type",
        payload=1.234,
        units="nats",
        metadata={"seed": 0, "nfe": 10},
    )
    assert r.units == "nats"
    assert r.metadata == {"seed": 0, "nfe": 10}


def test_observation_result_is_hashable():
    """Frozen dataclasses are hashable -- enables set/dict membership tests."""
    r1 = ObservationResult(kind=ObservationKind.ENDPOINT_BUNDLE, channel="a", payload=1)
    r2 = ObservationResult(kind=ObservationKind.ENDPOINT_BUNDLE, channel="a", payload=1)
    r3 = ObservationResult(kind=ObservationKind.ENDPOINT_BUNDLE, channel="b", payload=1)
    assert hash(r1) == hash(r2)
    assert {r1, r2, r3} == {r1, r3}


# --- AdapterObservationProtocol ---


def test_adapter_observation_protocol_is_runtime_checkable():
    """``@runtime_checkable`` enables ``isinstance`` checks (Wave 11 §1)."""
    assert getattr(AdapterObservationProtocol, "_is_runtime_protocol", False) is True


def test_isinstance_passes_for_compliant_observer():
    """A class with an ``observe`` method is structurally typed as conforming."""
    obs = MockObserverAll()
    assert isinstance(obs, AdapterObservationProtocol)


def test_isinstance_passes_for_empty_observer():
    """Empty-tuple observer is still conforming -- empty is a valid response."""
    obs = MockObserverEmpty()
    assert isinstance(obs, AdapterObservationProtocol)


def test_isinstance_fails_for_non_compliant_observer():
    """A class without ``observe`` does NOT conform (structural typing)."""
    obs = NonCompliantObserver()
    assert not isinstance(obs, AdapterObservationProtocol)


def test_assert_adapter_compliance_passes_for_compliant():
    """``assert_adapter_compliance`` accepts a class with the ``observe`` method."""
    assert_adapter_compliance(MockObserverAll)


def test_assert_adapter_compliance_raises_for_missing_observe():
    """Declared-but-non-compliant observer raises ``MissingProtocolError`` on enforcement."""
    with pytest.raises(MissingProtocolError) as exc:
        assert_adapter_compliance(DeclaredButMissingObserver)
    assert "AdapterObservationProtocol" in str(exc.value)


def test_observe_returns_tuple_of_observation_results():
    """The result of ``observe(...)`` is a tuple (immutable, ordered)."""
    obs = MockObserverAll()
    results = obs.observe(trace="trace", state="state")
    assert isinstance(results, tuple)
    assert len(results) == 4
    kinds = {r.kind for r in results}
    assert kinds == set(ObservationKind)


def test_observe_accepts_default_strategies_tuple():
    """The default ``strategies`` kwarg requests all four kinds (Wave 68 §4)."""
    import inspect

    sig = inspect.signature(AdapterObservationProtocol.observe)
    strategies_param = sig.parameters["strategies"]
    assert strategies_param.default == (
        ObservationKind.ENDPOINT_BUNDLE,
        ObservationKind.DISCRETE_TOKENS,
        ObservationKind.POSITION_ENTROPY_REDUCTION,
        ObservationKind.TRAJECTORY_NATIVE,
    )


def test_observe_threads_theta_after_to_payload_metadata():
    """``theta_after`` is forwarded to ``metadata`` for entropy-reduction wiring."""
    obs = MockObserverAll()
    results = obs.observe(
        trace="t",
        state="s",
        theta_before="prior",
        theta_after="posterior",
    )
    for r in results:
        assert r.metadata["theta_after"] == "posterior"
        assert r.metadata["theta_before"] == "prior"


def test_partial_observer_returns_only_supported_strategies():
    """Adapters that skip a strategy (Kanzi: no entropy reduction) return only what they support."""
    obs = MockObserverPartial()
    results = obs.observe(trace="t", state="s")
    assert len(results) == 1
    assert results[0].kind == ObservationKind.DISCRETE_TOKENS
    assert results[0].channel == "discrete_idx"
    assert results[0].payload == [0, 1, 2, 3]


def test_empty_observer_returns_empty_tuple_for_any_strategies():
    """Synthetic / ref adapters with no discrete observation return empty tuple."""
    obs = MockObserverEmpty()
    results = obs.observe(
        trace="t",
        state="s",
        strategies=(ObservationKind.DISCRETE_TOKENS, ObservationKind.POSITION_ENTROPY_REDUCTION),
    )
    assert results == ()


def test_observation_protocol_decorator_returns_class_unchanged():
    """``@implements(AdapterObservationProtocol)`` returns the class with the same name."""
    assert MockObserverAll.__name__ == "MockObserverAll"
    assert AdapterObservationProtocol in MockObserverAll.__protocols__


def test_observation_protocol_protocol_set_deduplication():
    """Multiple ``@implements`` calls deduplicate the Protocol set."""

    @implements(AdapterObservationProtocol)
    @implements(AdapterObservationProtocol)
    class Doubled:
        def observe(self, trace, state, paper_quantities=None, *, strategies=..., theta_before=None, theta_after=None):
            return ()

    protocols = list(Doubled.__protocols__)
    assert protocols.count(AdapterObservationProtocol) == 1
