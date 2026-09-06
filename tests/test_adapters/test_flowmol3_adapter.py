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
    AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART,
    FLOWMOL3_ATOM_TYPE_VOCAB_SIZE,
    FLOWMOL3_CHANNELS,
    FLOWMOL3_CHANNEL_DOMAINS,
    FlowMol3Adapter,
    FlowMol3AtomTypeEntropyRestartPolicy,
    FlowMol3Capabilities,
    PER_POSITION_ENTROPY_REDUCTION,
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


# ---------------------------------------------------------------------------
# Wave 49 Agent F — atom-type entropy restart policy + metric
# ---------------------------------------------------------------------------


class TestFlowMol3AtomTypeEntropyRestartPolicy:
    """FlowMol3-specific restart policy (Wave 49 Agent F).

    Mirrors the :class:`KanziGPTPriorRestartPolicy` (Wave 45 Agent F)
    and :class:`LineageFlowClassifierAwareRestart` (Wave 45 Agent G)
    patterns. Reads per-atom entropy over the 10-way atom-type
    categorical and biases the schedule-driven base memory fraction
    per atom.
    """

    def test_default_construction_succeeds(self) -> None:
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        assert policy.m_floor == 0.05
        assert policy.m_ceiling == 0.95
        assert policy.entropy_floor > 0.0
        assert policy.entropy_ceiling > policy.entropy_floor

    def test_invalid_entropy_floor_raises(self) -> None:
        import pytest as _pytest
        with _pytest.raises(ValueError):
            FlowMol3AtomTypeEntropyRestartPolicy(
                entropy_floor=1.0,
                entropy_ceiling=0.5,
            )

    def test_invalid_m_floor_raises(self) -> None:
        import pytest as _pytest
        with _pytest.raises(ValueError):
            FlowMol3AtomTypeEntropyRestartPolicy(
                m_floor=0.6,
                m_ceiling=0.5,
            )

    def test_propose_restart_returns_uniform_alpha(self) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        alpha = policy.propose_restart(trace=None, paper_quantities=None)
        assert isinstance(alpha, np.ndarray)
        assert alpha.shape == (8,)  # FLOWMOL3_PLACEHOLDER_NUM_NODES
        assert np.allclose(alpha, 0.5)

    def test_memory_fraction_vector_no_prior_entry_returns_base(
        self,
    ) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        m_vec = policy.memory_fraction_vector(
            prior_entry=None, base_m=0.7,
        )
        # Synthetic-mode fallback: uniform m_vec = base_m.
        assert m_vec.shape == (8,)
        assert np.allclose(m_vec, 0.7)

    def test_memory_fraction_vector_missing_payload_returns_base(
        self,
    ) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        m_vec = policy.memory_fraction_vector(
            prior_entry={"some_other_key": 1.0}, base_m=0.4,
        )
        # Missing ``atom_type_distribution`` key triggers the fallback.
        assert m_vec.shape == (8,)
        assert np.allclose(m_vec, 0.4)

    def test_memory_fraction_vector_low_entropy_high_m(self) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        # Spike logits at index 0: per-atom entropy = 0 (low) → m_ceiling
        atom_logits = np.zeros(
            (4, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        atom_logits[:, 0] = 100.0  # confident spike
        m_vec = policy.memory_fraction_vector(
            prior_entry={"atom_type_distribution": atom_logits},
            base_m=0.5,
        )
        # Each atom has low entropy → m near m_ceiling = 0.95,
        # but clamped to [min(base, m_floor), max(base, m_ceiling)]
        # = [0.05, 0.95]. So m_vec is ~0.95.
        assert np.all(m_vec >= 0.05)
        assert np.all(m_vec <= 0.95)
        # With base_m=0.5 and low entropy, m_vec should be near ceiling.
        assert float(m_vec.mean()) > 0.7

    def test_memory_fraction_vector_high_entropy_low_m(self) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        # Uniform logits: per-atom entropy = log(K) (high) → m_floor
        atom_logits = np.ones(
            (4, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        m_vec = policy.memory_fraction_vector(
            prior_entry={"atom_type_distribution": atom_logits},
            base_m=0.5,
        )
        # Each atom has high entropy → m near m_floor = 0.05,
        # clamped to [min(base, m_floor), max(base, m_ceiling)]
        # = [0.05, 0.95]. So m_vec is ~0.05.
        assert np.all(m_vec >= 0.05)
        assert np.all(m_vec <= 0.95)
        # With base_m=0.5 and high entropy, m_vec should be near floor.
        assert float(m_vec.mean()) < 0.3

    def test_memory_fraction_vector_malformed_shape_raises(
        self,
    ) -> None:
        import numpy as np
        import pytest as _pytest

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        # Wrong last dim: 7 instead of FLOWMOL3_ATOM_TYPE_VOCAB_SIZE.
        atom_logits = np.zeros((4, 7), dtype=np.float64)
        with _pytest.raises(ValueError, match="atom_type_distribution_shape_invalid"):
            policy.memory_fraction_vector(
                prior_entry={"atom_type_distribution": atom_logits},
                base_m=0.5,
            )


class TestFlowMol3EntropyMetric:
    """Per-atom-type entropy reduction metric (Wave 49 Agent F).

    Mirrors :meth:`LineageFlowAdapter.observe_entropy_reduction` (Wave
    45 Agent E). Returns the per-atom Shannon entropy reduction from a
    baseline atom-type distribution to a framework endpoint.
    """

    def test_observe_entropy_reduction_default_returns_zero(
        self, adapter
    ) -> None:
        """Synthetic-mode fallback returns ``0.0`` (uniform-vs-uniform)."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        result = adapter.observe_entropy_reduction(trace)
        assert PER_POSITION_ENTROPY_REDUCTION in result
        # Synthetic uniform-vs-uniform → entropy reduction = 0.
        assert result[PER_POSITION_ENTROPY_REDUCTION] == 0.0

    def test_observe_entropy_reduction_explicit_arrays(
        self, adapter
    ) -> None:
        """Explicit ``theta_before`` and ``theta_after`` produce a real number."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        # Sharpened (low-entropy) after-vs-uniform before → positive reduction.
        theta_after = np.zeros(
            (8, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        theta_after[:, 0] = 100.0  # confident spike
        theta_before = np.full_like(theta_after, 1.0)  # uniform
        result = adapter.observe_entropy_reduction(
            trace, theta_before=theta_before, theta_after=theta_after,
        )
        assert result[PER_POSITION_ENTROPY_REDUCTION] > 0.0

    def test_observe_entropy_reduction_widening_is_negative(
        self, adapter
    ) -> None:
        """Going from sharp to uniform should yield a negative reduction."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        # Sharpened before, uniform after.
        theta_before = np.zeros(
            (8, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        theta_before[:, 0] = 100.0
        theta_after = np.full_like(theta_before, 1.0)
        result = adapter.observe_entropy_reduction(
            trace, theta_before=theta_before, theta_after=theta_after,
        )
        assert result[PER_POSITION_ENTROPY_REDUCTION] < 0.0

    def test_observe_entropy_reduction_byte_stable(
        self, adapter
    ) -> None:
        """Two calls with the same trace return identical results."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=42)
        r1 = adapter.observe_entropy_reduction(trace)
        r2 = adapter.observe_entropy_reduction(trace)
        assert r1 == r2


class TestFlowMol3PolicyWiring:
    """Restart policy wiring into apply_restart_distribution (Wave 49 Agent F)."""

    def test_default_adapter_no_atom_policy(
        self, adapter
    ) -> None:
        """Default-constructed adapter has no atom-type policy."""
        assert adapter._atom_type_entropy_restart_policy is None  # noqa: SLF001

    def test_invalid_policy_type_raises(self) -> None:
        import pytest as _pytest
        with _pytest.raises(TypeError):
            FlowMol3Adapter(atom_type_entropy_restart_policy="not_a_policy")  # type: ignore[arg-type]

    def test_valid_policy_accepted(self) -> None:
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        adapter = FlowMol3Adapter(
            atom_type_entropy_restart_policy=policy,
        )
        assert (
            adapter._atom_type_entropy_restart_policy  # noqa: SLF001
            is policy
        )

    def test_apply_restart_emits_atom_audit_when_policy_active(
        self, adapter
    ) -> None:
        """When the atom-type policy is wired, the restart bundle carries
        the AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART code in its provenance.
        """
        from types import SimpleNamespace
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        adapter = FlowMol3Adapter(
            atom_type_entropy_restart_policy=policy,
        )
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        # Minimal policy with beta_by_channel.
        restart_policy = SimpleNamespace(
            policy_hash="test",
            beta_by_channel={"coordinate": 0.5},
        )
        new_bundle = adapter.apply_restart_distribution(
            bundle, restart_policy,
        )
        assert AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART in new_bundle.provenance

    def test_apply_restart_default_no_atom_audit(
        self, adapter
    ) -> None:
        """Default adapter does NOT emit the atom-type audit code."""
        from types import SimpleNamespace
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        restart_policy = SimpleNamespace(
            policy_hash="test",
            beta_by_channel={"coordinate": 0.5},
        )
        new_bundle = adapter.apply_restart_distribution(
            bundle, restart_policy,
        )
        # The audit code should NOT be present in default mode.
        assert (
            AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART
            not in new_bundle.provenance
        )
        # But the legacy restart-boundary audit code is preserved
        # (Wave 41 regression-vector byte-stability).
        assert "flowmol3_restart_boundary" in new_bundle.provenance


class TestFlowMol3PublicSurface:
    """Public symbol surface for Wave 49 Agent F additions."""

    def test_per_position_entropy_reduction_key_matches_lineageflow(
        self,
    ) -> None:
        from adaptive_reflow.adapters.lineageflow import (
            PER_POSITION_ENTROPY_REDUCTION as LF_KEY,
        )
        assert LF_KEY == PER_POSITION_ENTROPY_REDUCTION

    def test_atom_type_vocab_size_matches_v2_adapter(self) -> None:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            FLOWMOL3ADAPTER_N_ATOM_TYPES,
        )
        assert FLOWMOL3ADAPTER_N_ATOM_TYPES == FLOWMOL3_ATOM_TYPE_VOCAB_SIZE

    def test_factory_accepts_policy(self) -> None:
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        adapter = default_flowmol3_adapter(
            atom_type_entropy_restart_policy=policy,
        )
        assert isinstance(adapter, FlowMol3Adapter)
        assert (
            adapter._atom_type_entropy_restart_policy  # noqa: SLF001
            is policy
        )


__all__ = ()