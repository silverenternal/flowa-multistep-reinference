"""Hand-written tests for :class:`ToyGaussianAdapter` (Wave 15 C — D.3).

The :class:`ToyGaussianAdapter` is the second universal-layer
worked example (alongside :class:`ToyLinearAdapter`). It exists to
prove the public engine + adapter Protocol surface is universal: a
1D Gaussian mixture ODE ``dx/dt = -x + target_mean`` driven through
the same :class:`Engine.run_round` path as a molecular FM model,
without any reference to :mod:`adaptive_reflow.molecular`.

This test file covers (Wave 15 C — D.3 ≥ 10 tests):

* Capabilities handshake (5)
* Lifecycle (3)
* Native-state semantics (3)
* Injection / byte-stability (2)
* Helper purity (gauss_score) (1)

Total: **14 tests** (Wave 15 C D.3 floor: 10).
"""
from __future__ import annotations

import pytest

from adaptive_reflow.adapters.toy_gaussian import (
    EULER_DT,
    EULER_NUM_STEPS,
    GaussianAdapterCapabilities,
    INITIAL_MEANS,
    INITIAL_STDDEVS,
    INITIAL_WEIGHTS,
    SUPPORTED_CHANNELS,
    ToyGaussianAdapter,
    default_toy_gaussian_adapter,
    gauss_score,
)
from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    ODEIntegratorTrace,
    StateBundle,
)
from adaptive_reflow.universal import (
    ArtifactHash,
    FlowMatchingODEAdapter,
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
def adapter() -> ToyGaussianAdapter:
    return default_toy_gaussian_adapter()


@pytest.fixture
def adapter_custom() -> ToyGaussianAdapter:
    """Adapter with overridden dt / num_steps so the lifecycle tests
    observe step-dependent digests without colliding with the default
    config."""
    return ToyGaussianAdapter(dt=0.5, num_steps=2)


# ---------------------------------------------------------------------------
# Capabilities handshake
# ---------------------------------------------------------------------------


class TestToyGaussianCapabilities:
    def test_capabilities_returns_adapter_capabilities_instance(
        self, adapter
    ) -> None:
        assert isinstance(adapter.capabilities(), AdapterCapabilities)

    def test_capabilities_has_all_protocol_surface_flags(
        self, adapter
    ) -> None:
        caps = adapter.capabilities()
        assert caps.has_ode_integration_surface is True
        assert caps.has_prior_export is True
        assert caps.has_state_export is True
        assert caps.has_condition_injection is True
        assert caps.has_restart_boundary is True
        assert caps.has_continuous_channels is True
        assert caps.has_discrete_channels is False
        assert caps.has_trajectory_digest is True
        assert caps.has_deterministic_seed is True
        assert caps.has_materialization_route is True

    def test_capabilities_supported_channels_is_one_x(
        self, adapter
    ) -> None:
        caps = adapter.capabilities()
        assert caps.supported_channels == SUPPORTED_CHANNELS
        assert caps.supported_channels == (ChannelName("x"),)

    def test_capabilities_channel_domain_is_continuous(
        self, adapter
    ) -> None:
        caps = adapter.capabilities()
        assert caps.channel_domains == {ChannelName("x"): "continuous"}

    def test_capabilities_required_mixer_is_noop(self, adapter) -> None:
        caps = adapter.capabilities()
        assert caps.required_mixer is NoOpMixer


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestToyGaussianLifecycle:
    def test_build_initial_state_is_valid_state_bundle(
        self, adapter
    ) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        assert isinstance(bundle, StateBundle)
        ok, errs = validate_state_bundle(bundle)
        assert ok, errs

    def test_build_initial_state_detach_proof_true(
        self, adapter
    ) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        assert bundle.detach_proof is True

    def test_solve_ode_produces_euler_steps_in_native_state(
        self, adapter
    ) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"target_mean": 1.0},
            source="test_toy_gaussian",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        assert isinstance(trace, ODEIntegratorTrace)
        assert trace.steps == EULER_NUM_STEPS


# ---------------------------------------------------------------------------
# Native-state semantics
# ---------------------------------------------------------------------------


class TestToyGaussianNativeState:
    def test_native_state_records_initial_mixture_params(
        self, adapter
    ) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        # The adapter stores the canonical initial mixture (see
        # INITIAL_WEIGHTS / INITIAL_MEANS / INITIAL_STDDEVS) under the
        # bundle's native-state digest.
        native = adapter._native_states[bundle.native_state_digest]
        assert native["weights"] == INITIAL_WEIGHTS
        assert native["means"] == INITIAL_MEANS
        assert native["stddevs"] == INITIAL_STDDEVS

    def test_apply_restart_blends_toward_initial(
        self, adapter_custom
    ) -> None:
        bundle = adapter_custom.build_initial_state(
            batch_id="b", sample_id="s"
        )
        policy = RestartPolicy(
            policy_id="p-1",
            writer_id="test",
            run_id="r-1",
            target_round=1,
            outer_cycle_id=0,
            beta_by_channel={ChannelName("x"): 0.0},  # full retain
            alpha_by_channel={ChannelName("x"): 1.0},
            fresh_noise_floor_by_channel={ChannelName("x"): 0.0},
            schedule_sample=None,
            freeze_admission_by_channel={ChannelName("x"): True},
            ledger_row_id="lr-1",
            policy_hash=ArtifactHash(""),
            created_at_round=0,
        )
        new_bundle = adapter_custom.apply_restart_distribution(
            bundle, policy
        )
        # Full retain → blended == prior.
        prior = adapter_custom._native_states[bundle.native_state_digest]
        post = adapter_custom._native_states[new_bundle.native_state_digest]
        assert post["weights"] == prior["weights"]
        assert post["means"] == prior["means"]
        assert post["stddevs"] == prior["stddevs"]

    def test_apply_restart_with_missing_native_state_raises(
        self, adapter
    ) -> None:
        # Construct a fresh bundle, run ``solve_ode`` to populate the
        # native-state cache, then mutate the cache (simulate eviction)
        # so the bundle's digest is no longer present. ``StateBundle``
        # is frozen, so we exercise the cache-miss path through the
        # adapter's own helpers rather than via attribute mutation.
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"target_mean": 0.5},
            source="test_toy_gaussian",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        # Manually evict the bundle's digest from the native-state
        # cache; this is what would happen under memory pressure in
        # production.
        adapter._native_states.pop(bundle.native_state_digest, None)
        # Calling ``apply_restart_distribution`` on the now-evicted
        # bundle raises a typed ``CapabilityMissingError`` (the
        # engine's fail-closed path catches it).
        policy = RestartPolicy(
            policy_id="p-1",
            writer_id="test",
            run_id="r-1",
            target_round=1,
            outer_cycle_id=0,
            beta_by_channel={ChannelName("x"): 0.5},
            alpha_by_channel={ChannelName("x"): 0.5},
            fresh_noise_floor_by_channel={ChannelName("x"): 0.0},
            schedule_sample=None,
            freeze_admission_by_channel={ChannelName("x"): True},
            ledger_row_id="lr-1",
            policy_hash=ArtifactHash(""),
            created_at_round=0,
        )
        with pytest.raises(CapabilityMissingError):
            adapter.apply_restart_distribution(bundle, policy)
        # ``trace.native_state_digest`` is a separate cache key
        # (recorded by ``solve_ode``); only the bundle's digest is
        # evicted here, so the trace's record is unaffected.
        assert trace.native_state_digest in adapter._native_states


# ---------------------------------------------------------------------------
# Injection / byte-stability
# ---------------------------------------------------------------------------


class TestToyGaussianInjectionByteStable:
    def test_inject_forward_noise_perturbation_changes_digest(
        self, adapter
    ) -> None:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        new_bundle = adapter.inject_forward_noise(bundle, injected=0.5)
        assert new_bundle.native_state_digest != bundle.native_state_digest
        assert "inject_forward_noise_applied" in new_bundle.provenance

    def test_two_solve_ode_with_same_seed_are_byte_identical(
        self, adapter
    ) -> None:
        b1 = adapter.build_initial_state(batch_id="b", sample_id="s")
        b2 = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"target_mean": 0.5},
            source="test_toy_gaussian",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        t1 = adapter.solve_ode(b1, cond, seed=42)
        t2 = adapter.solve_ode(b2, cond, seed=42)
        assert t1.native_state_digest == t2.native_state_digest
        assert t1.integrator_config_hash == t2.integrator_config_hash


# ---------------------------------------------------------------------------
# Helper purity (gauss_score)
# ---------------------------------------------------------------------------


class TestToyGaussianHelpers:
    def test_gauss_score_zero_at_mean(self) -> None:
        # ``gauss_score(mean, mean, stddev) = 1/(stddev*sqrt(2*pi))``;
        # for stddev=1.0 this is the standard-normal PDF peak.
        s = gauss_score(0.0, 0.0, 1.0)
        import math

        assert abs(s - 1.0 / math.sqrt(2.0 * math.pi)) < 1e-12

    def test_gauss_score_rejects_nonpositive_stddev(self) -> None:
        with pytest.raises(ValueError):
            gauss_score(0.0, 0.0, 0.0)
        with pytest.raises(ValueError):
            gauss_score(0.0, 0.0, -1.0)


# ---------------------------------------------------------------------------
# Adapter-as-Protocol confirmation
# ---------------------------------------------------------------------------


def test_adapter_satisfies_flow_matching_ode_adapter_protocol(
    adapter: ToyGaussianAdapter,
) -> None:
    assert isinstance(adapter, FlowMatchingODEAdapter)


__all__ = ()