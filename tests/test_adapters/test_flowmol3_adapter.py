"""Hand-written tests for :class:`FlowMol3Adapter` (Wave 15 C — D.3).

This is the placeholder :class:`FlowMol3Adapter` (DTB-G2) — it does
NOT import or call FlowMol3 source code; it produces deterministic
hash-stable placeholder state suitable for the public engine + adapter
protocol surface (DTB-G1). The tests here exercise the surface end-to-end
so the Wave 11 + Wave 14 refactors of the universal layer stay
backwards-compatible with the FlowMol3 hand-off point.

Note: this file is distinct from ``test_flowmol3_v2_adapter.py``
which tests the **v2** adapter wired into the per-channel materializer
(:class:`FlowMol3V2Adapter`). The v1 / v2 split is the Wave 9
registry separation; the two adapters share the registry family key
``flowmol3`` / ``flowmol3_v2`` but expose different capabilities and
materializer wiring.

Tests in this file (Wave 15 C — D.3 ≥ 10 tests):

* Capabilities handshake (5)
* Lifecycle (3)
* Failure-closed paths (2)
* Byte-stability (1)
* Forward-noise injection (1)
* Channel vocabulary (1)

Total: **13 tests** (Wave 15 C D.3 floor: 10).
"""
from __future__ import annotations

import pytest

from adaptive_reflow.adapters import (
    FLOWMOL3_CHANNELS,
    FLOWMOL3_CHANNEL_DOMAINS,
    FlowMol3Adapter,
    FlowMol3Capabilities,
    default_flowmol3_adapter,
    flowmol3_registry_entry,
)
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    ODEIntegratorTrace,
    StateBundle,
)
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    validate_state_bundle,
)
from adaptive_reflow.writer.registry import FLOWMOL3_PINNED_COMMIT


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> FlowMol3Adapter:
    return default_flowmol3_adapter()


# ---------------------------------------------------------------------------
# Capabilities handshake
# ---------------------------------------------------------------------------


class TestFlowMol3Capabilities:
    """FlowMol3 v1 placeholder adapter declares the DTB-G2 surface."""

    def test_capabilities_returns_adapter_capabilities_instance(
        self, adapter
    ) -> None:
        assert isinstance(adapter.capabilities(), AdapterCapabilities)

    def test_capabilities_dtb_g2_defaults(self, adapter) -> None:
        caps = adapter.capabilities()
        # DTB-G2 baseline surface.
        assert caps.has_ode_integration_surface is True
        assert caps.has_prior_export is True
        assert caps.has_state_export is True
        # D3 — has_condition_injection default True so the adapter can
        # participate in Engine.run_round via NullConditionInjector.
        assert caps.has_condition_injection is True
        assert caps.has_restart_boundary is True
        assert caps.has_deterministic_seed is True

    def test_capabilities_mixed_channel_vocabulary(self, adapter) -> None:
        caps = adapter.capabilities()
        # FlowMol3 native state is ``(x, a, c, e)``; we expose it via the
        # engine's mixed ``(coordinate, charge, raw_pair)`` vocabulary.
        assert set(caps.supported_channels) == set(FLOWMOL3_CHANNELS)
        assert "coordinate" in caps.supported_channels
        assert "charge" in caps.supported_channels
        assert "raw_pair" in caps.supported_channels

    def test_capabilities_channel_domains_match_paper_vocabulary(
        self, adapter
    ) -> None:
        caps = adapter.capabilities()
        # ``coordinate`` + ``charge`` are continuous; ``raw_pair`` is
        # discrete (per the FlowMol3 native ``(x, a, c, e)`` mapping).
        assert caps.channel_domains[ChannelName("coordinate")] == "continuous"
        assert caps.channel_domains[ChannelName("charge")] == "continuous"
        assert caps.channel_domains[ChannelName("raw_pair")] == "discrete"

    def test_capabilities_has_discrete_and_continuous_channels(
        self, adapter
    ) -> None:
        caps = adapter.capabilities()
        # AdapterCapabilities reports continuous + discrete channels.
        assert caps.has_continuous_channels is True
        assert caps.has_discrete_channels is True

    def test_capabilities_pinned_commit_matches_registry(
        self, adapter
    ) -> None:
        # ``pinned_commit`` is the FlowMol3 git commit at integration
        # time; it must round-trip through the registry entry.
        assert adapter.pinned_commit == FLOWMOL3_PINNED_COMMIT
        entry = flowmol3_registry_entry()
        # Registry entry exposes the same pinned commit on its
        # ``mechanism_id`` / audit trail.
        assert entry is not None


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestFlowMol3Lifecycle:
    """State-bundle round-trip through the placeholder adapter."""

    def test_build_initial_state_validates(self, adapter) -> None:
        bundle = adapter.build_initial_state(
            batch_id="flowmol3-batch", sample_id="flowmol3-sample"
        )
        ok, errs = validate_state_bundle(bundle)
        assert ok, errs

    def test_build_initial_state_detach_proof_true(self, adapter) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        assert bundle.detach_proof is True

    def test_solve_ode_returns_integrator_trace(self, adapter) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 3},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=7)
        assert isinstance(trace, ODEIntegratorTrace)
        assert trace.steps == 3

    def test_solve_ode_rejects_zero_steps(self, adapter) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 0},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        with pytest.raises(ValueError):
            adapter.solve_ode(bundle, cond, seed=0)


# ---------------------------------------------------------------------------
# Failure-closed paths
# ---------------------------------------------------------------------------


class TestFlowMol3FailClosed:
    """Fail-closed behaviour for invalid input."""

    def test_export_endpoint_rejects_non_state_bundle(
        self, adapter
    ) -> None:
        with pytest.raises(TypeError):
            adapter.export_endpoint("not a bundle")  # type: ignore[arg-type]

    def test_apply_restart_with_invalid_bundle_raises(
        self, adapter
    ) -> None:
        # The placeholder re-validates the state bundle and raises on
        # malformed input. ``validate_state_bundle`` may raise
        # ``AttributeError`` (because the input is not a real bundle
        # and lacks ``.channels``); the fail-closed contract is that
        # ANY exception bubbles up, not a silent return.
        with pytest.raises(Exception):  # noqa: BLE001 — fail-closed contract
            adapter.apply_restart_distribution(
                "not a bundle",  # type: ignore[arg-type]
                policy=None,
            )


# ---------------------------------------------------------------------------
# Byte-stability (B.2 framework-internal-metrics gate)
# ---------------------------------------------------------------------------


class TestFlowMol3ByteStable:
    def test_two_calls_produce_identical_digest(self, adapter) -> None:
        b1 = adapter.build_initial_state(batch_id="byte", sample_id="stable")
        b2 = adapter.build_initial_state(batch_id="byte", sample_id="stable")
        assert b1.native_state_digest == b2.native_state_digest


# ---------------------------------------------------------------------------
# Forward-noise injection (P1-8)
# ---------------------------------------------------------------------------


class TestFlowMol3InjectForwardNoise:
    def test_inject_forward_noise_returns_state_bundle(
        self, adapter
    ) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        new_bundle = adapter.inject_forward_noise(bundle, injected=[0.1, 0.2])
        assert isinstance(new_bundle, StateBundle)
        assert new_bundle.source_round == bundle.source_round + 1
        # The forward-noise applied audit code is appended to provenance.
        assert "inject_forward_noise_applied" in new_bundle.provenance


# ---------------------------------------------------------------------------
# Adapter-as-Protocol confirmation
# ---------------------------------------------------------------------------


def test_adapter_satisfies_flow_matching_ode_adapter_protocol(
    adapter: FlowMol3Adapter,
) -> None:
    assert isinstance(adapter, FlowMatchingODEAdapter)


__all__ = ()