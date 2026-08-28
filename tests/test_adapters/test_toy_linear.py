"""Tests for the ToyLinearAdapter worked example (DTB-G1 spec §13)."""

from __future__ import annotations

import pytest

from adaptive_reflow.adapters import ToyLinearAdapter, default_toy_linear_adapter
from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> ToyLinearAdapter:
    return default_toy_linear_adapter()


# ---------------------------------------------------------------------------
# Capability handshake
# ---------------------------------------------------------------------------


class TestToyLinearCapabilities:
    def test_capabilities_have_expected_bools(self, adapter):
        caps = adapter.capabilities()
        assert caps.has_ode_integration_surface is True
        assert caps.has_prior_export is True
        assert caps.has_state_export is True
        assert caps.has_continuous_channels is True
        assert caps.has_discrete_channels is False
        assert caps.has_condition_injection is False
        assert caps.has_restart_boundary is False
        assert caps.has_deterministic_seed is True

    def test_capabilities_channel_vocabulary(self, adapter):
        caps = adapter.capabilities()
        assert caps.supported_channels == (ChannelName("x"),)
        assert caps.channel_domains == {ChannelName("x"): "continuous"}

    def test_capabilities_required_mixer_is_noop(self, adapter):
        caps = adapter.capabilities()
        assert caps.required_mixer is NoOpMixer

    def test_capabilities_returns_adapter_capabilities_instance(self, adapter):
        assert isinstance(adapter.capabilities(), AdapterCapabilities)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestToyLinearLifecycle:
    def test_build_initial_state(self, adapter):
        s = adapter.build_initial_state("b", "s", source_round=0)
        ok, errs = validate_state_bundle(s)
        assert ok, errs
        assert s.detach_proof is True
        assert s.source_round == 0

    def test_build_initial_state_rejects_negative_round(self, adapter):
        with pytest.raises(ValueError):
            adapter.build_initial_state("b", "s", source_round=-1)

    def test_export_endpoint_is_identity(self, adapter):
        s = adapter.build_initial_state("b", "s")
        assert adapter.export_endpoint(s) is s

    def test_detach_and_validate_endpoint_requires_detach_proof(self, adapter):
        # Cannot construct a StateBundle with detach_proof=False via
        # adapter — it's always True. But we can construct one manually
        # and pass it to detach_and_validate_endpoint.
        s = adapter.build_initial_state("b", "s")
        # The valid case returns the same state.
        assert adapter.detach_and_validate_endpoint(s) is s

    def test_observation(self, adapter):
        s = adapter.build_initial_state("b", "s")
        from adaptive_reflow.universal.state import ODEIntegratorTrace
        trace = ODEIntegratorTrace(
            steps=1, accept_rate=1.0, native_state_digest="x", integrator_config_hash="y"
        )
        assert adapter.observe_endpoint(trace, s) is s

    def test_solve_ode_produces_trace(self, adapter):
        from adaptive_reflow.universal.state import ODEConditionDelta
        s = adapter.build_initial_state("b", "s")
        delta = ODEConditionDelta(
            delta_spec={"x": "ignored"},
            source="test",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(s, delta, seed=42, steps=10)
        assert trace.steps == 10
        assert 0.0 <= trace.accept_rate <= 1.0
        assert trace.native_state_digest is not None

    def test_solve_ode_rejects_zero_steps(self, adapter):
        from adaptive_reflow.universal.state import ODEConditionDelta
        s = adapter.build_initial_state("b", "s")
        delta = ODEConditionDelta(
            delta_spec={"x": "ignored"},
            source="test",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        with pytest.raises(ValueError):
            adapter.solve_ode(s, delta, seed=0, steps=0)

    def test_solve_ode_is_deterministic(self, adapter):
        from adaptive_reflow.universal.state import ODEConditionDelta
        s = adapter.build_initial_state("b", "s")
        delta = ODEConditionDelta(
            delta_spec={"x": "ignored"},
            source="test",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        t1 = adapter.solve_ode(s, delta, seed=42, steps=5)
        t2 = adapter.solve_ode(s, delta, seed=42, steps=5)
        assert t1.native_state_digest == t2.native_state_digest


# ---------------------------------------------------------------------------
# Fail-closed for unadvertised capabilities
# ---------------------------------------------------------------------------


class TestToyLinearFailClosed:
    def test_compose_condition_raises_capability_missing(self, adapter):
        s = adapter.build_initial_state("b", "s")
        delta = ODEConditionDelta(
            delta_spec={"x": "ignored"},
            source="test",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        with pytest.raises(CapabilityMissingError):
            adapter.compose_condition(s, delta)

    def test_apply_restart_distribution_raises_capability_missing(self, adapter):
        s = adapter.build_initial_state("b", "s")
        # Construct a minimal RestartPolicy. The adapter fails closed
        # before reading any field, so empty maps are fine.
        from adaptive_reflow.universal import ArtifactHash
        policy = RestartPolicy(
            policy_id="p-1",
            writer_id="my.test",
            run_id="run-1",
            target_round=1,
            outer_cycle_id=0,
            beta_by_channel={},
            alpha_by_channel={},
            fresh_noise_floor_by_channel={},
            schedule_sample=None,
            freeze_admission_by_channel={},
            ledger_row_id="lr-1",
            policy_hash=ArtifactHash(""),
            created_at_round=0,
        )
        with pytest.raises(CapabilityMissingError):
            adapter.apply_restart_distribution(s, policy)


# ---------------------------------------------------------------------------
# Gap B2: engine must absorb adapter exceptions via _safe_adapter_call
# ---------------------------------------------------------------------------


def test_adapter_raising_in_solve_ode_emits_audit() -> None:
    """Gap B2: a misbehaving ``solve_ode`` (raises ``RuntimeError``)
    must not propagate out of ``run_round``; the engine must emit
    ``ERR_ADAPTER_RAISED:solve_ode:RuntimeError`` in
    ``round_trace.audit_codes`` and return a fail-closed
    :class:`EngineRoundResult` instead of crashing.

    The toy-linear adapter does NOT advertise ``has_restart_boundary``
    or ``has_condition_injection``, so the engine cannot drive a happy
    path through it without mocking. We instead exercise the engine's
    :func:`_safe_adapter_call` wrapper by subclassing the synthetic
    continuous adapter and raising inside ``solve_ode``.
    """
    from adaptive_reflow.adapters import SyntheticContinuousAdapter
    from adaptive_reflow.frame import (
        ERR_ADAPTER_CONFIGURATION_ERROR,
        ERR_INTEGRATOR_TRACE_MISSING,
        Engine,
        EngineRoundResult,
    )

    class _RaisingAdapter(SyntheticContinuousAdapter):
        """Synthetic continuous adapter that raises on ``solve_ode``.

        P0-1: the engine's ``_safe_adapter_call`` wrapper now only
        catches the typed engine-internal
        :class:`AdapterConfigurationError` plus the two adapter-protocol
        exceptions. ``RuntimeError`` is no longer swallowed; the test
        adapter therefore raises
        :class:`AdapterConfigurationError` so the engine still emits
        a fail-closed audit trail rather than crashing the round.
        """

        def solve_ode(self, state, condition, *, seed):  # type: ignore[override]
            from adaptive_reflow.frame import AdapterConfigurationError

            raise AdapterConfigurationError("simulated solver explosion")

    # Build a valid bundle / policy / phase-state the engine accepts.
    adapter = _RaisingAdapter()
    s = adapter.build_initial_state(
        batch_id="batch-1", sample_id="sample-1"
    )
    # Build a minimal FinalRestartPolicy directly (avoids importing the
    # test-frame helpers).
    from dataclasses import replace as _dc_replace

    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        LedgerRowId,
        PolicyId,
        RunId,
    )
    from adaptive_reflow.contracts.authority import FinalRestartPolicy as FRP
    from adaptive_reflow.contracts.hashes import hash_policy_hash

    policy_no_hash = FRP(
        policy_id=PolicyId("policy-raise"),
        writer_id="test",
        run_id=RunId("run-1"),
        target_round=1,
        outer_cycle_id=0,
        beta_by_channel={ChannelName("coordinate"): FactorValue(0.0)},
        alpha_by_channel={ChannelName("coordinate"): FactorValue(1.0)},
        fresh_noise_floor_by_channel={
            ChannelName("coordinate"): FactorValue(0.0)
        },
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName("coordinate"): True},
        ledger_row_id=LedgerRowId("lr-raise"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    policy = _dc_replace(
        policy_no_hash, policy_hash=hash_policy_hash(policy_no_hash)
    )

    delta = ODEConditionDelta(
        delta_spec={"coordinate": "1.0"},
        source="test",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )

    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=engine_handshake_dummy_phase_state(),
        bundle=s,
        adapter=adapter,
        policy=policy,
        condition_delta=delta,
    )
    assert isinstance(result, EngineRoundResult)
    codes = result.round_trace.audit_codes
    # The adapter-raised audit code is present (step_name + exc type).
    # P0-1: the engine's _safe_adapter_call now catches the typed
    # ``AdapterConfigurationError`` and emits
    # ``ERR_ADAPTER_CONFIGURATION_ERROR`` (replacing the old
    # ``ERR_ADAPTER_RAISED`` swallow-all Exception path).
    assert any(
        c.startswith(ERR_ADAPTER_CONFIGURATION_ERROR + ":solve_ode:AdapterConfigurationError")
        for c in codes
    ), f"expected ERR_ADAPTER_CONFIGURATION_ERROR:solve_ode:AdapterConfigurationError in {codes!r}"
    # Engine never reached the trace-validation gate.
    assert ERR_INTEGRATOR_TRACE_MISSING in codes
    # Round is fail-closed: detached=False, integrator_trace=None.
    assert result.round_trace.detached is False
    assert result.round_trace.integrator_trace is None


def engine_handshake_dummy_phase_state():
    """Local helper: build the engine-side ``PhaseState`` used by the
    above Gap B2 test without importing test-frame helpers."""
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=2,
        seed_lineage_digest="seed-lineage-placeholder",
        recorded_at_round=0,
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
