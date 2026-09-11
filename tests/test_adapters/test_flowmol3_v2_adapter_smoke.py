"""Comprehensive test suite for the FlowMol3V2Adapter (DTB-G2 mechanics-adapter).

The :class:`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter`
wraps the zavalab FlowMol3 unconditional 3D molecule generator
(commit ``77cae22174b7792b0e25e9e0414038420736d841``) in the
framework's :class:`FlowMatchingODEAdapter` Protocol. The default
test backend is the deterministic NumPy synthetic field
(``backend="numpy"``); the ``torch`` backend is wired through
:meth:`_load_model` and is reserved for the production SOTA harness.

Tests:

* ``test_capabilities_handshake`` — the capability surface advertises
  the design-spec fields and validates via the universal
  :func:`validate_capabilities`.
* ``test_build_initial_state_returns_correct_shape`` —
  :meth:`build_initial_state` returns a well-formed
  :class:`StateBundle` with hash-stable ``TensorRef`` channels.
* ``test_solve_ode_returns_finite_trace`` — :meth:`solve_ode` returns
  a finite :class:`ODEIntegratorTrace` with the per-step
  ``(x, a, c, e)`` lineage stored under the trajectory digest.
* ``test_endpoint_round_trip`` — :meth:`solve_ode` followed by
  :meth:`observe_endpoint` returns a :class:`StateBundle` whose
  ``native_state_digest`` resolves to the ``(n_atoms, 3)`` coordinate
  final state.
* ``test_determinism`` — two identical ``(batch_id, sample_id)`` inputs
  produce byte-identical ``native_state_digest`` strings across two
  adapter instances.
* ``test_velocity_field_lazy_loads_torch_if_required`` —
  ``backend="torch"`` raises :class:`ImportError` when torch is not
  installed; the default ``backend="numpy"`` does not require torch.
* ``test_protocol_conformance`` — the adapter satisfies the
  ``@runtime_checkable`` Protocol check via ``isinstance``.
* ``test_restart_blend_channel_aware`` —
  :meth:`apply_restart_distribution` produces a detached bundle whose
  ``native_state_digest`` differs from the input and whose
  ``source_round`` increments.
* ``test_compose_condition_rejects_channel_keys`` —
  :meth:`compose_condition` rejects non-empty channel-keyed deltas
  with :class:`CapabilityMissingError("has_condition_injection")`.
* ``test_export_trajectory_returns_lineage`` —
  :meth:`export_trajectory` returns the per-step
  ``(traj_x, traj_c, traj_e, traj_a)`` lineage.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest

from adaptive_reflow.adapters.flowmol3_v2_adapter import (
    AUDIT_FLOWMOL3_RESTART_BLEND,
    AUDIT_FLOWMOL3_TRAJECTORY_BUILT,
    FLOWMOL3ADAPTER_CHANNEL_DOMAINS,
    FLOWMOL3ADAPTER_CHANNELS,
    FLOWMOL3ADAPTER_CONFIG_HASH,
    FLOWMOL3ADAPTER_CONFIG_VERSION,
    FLOWMOL3ADAPTER_MECHANISM_ID,
    FLOWMOL3ADAPTER_N_ATOM_TYPES,
    FLOWMOL3ADAPTER_PINNED_COMMIT,
    FLOWMOL3ADAPTER_STATE_SHAPE,
    FlowMol3V2AdapterCapabilities,
    FlowMol3V2Adapter,
    default_flowmol3adapter,
)
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
    validate_capabilities,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_final_policy(
    *,
    policy_id: str = "flowmol3adapter-test",
    run_id: str = "flowmol3adapter-test-run",
    beta: float = 0.5,
    target_round: int = 0,
) -> object:  # FinalRestartPolicy
    from adaptive_reflow.contracts import (
        ArtifactHash,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    coord_channel = ChannelName("coordinate")
    charge_channel = ChannelName("charge")
    pair_channel = ChannelName("raw_pair")
    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={
            coord_channel: FactorValue(float(beta)),
            charge_channel: FactorValue(float(beta)),
            pair_channel: FactorValue(float(beta)),
        },
        alpha_by_channel={
            coord_channel: FactorValue(1.0),
            charge_channel: FactorValue(1.0),
            pair_channel: FactorValue(1.0),
        },
        fresh_noise_floor_by_channel={
            coord_channel: FactorValue(0.0),
            charge_channel: FactorValue(0.0),
            pair_channel: FactorValue(0.0),
        },
        schedule_sample=None,
        freeze_admission_by_channel={
            coord_channel: True,
            charge_channel: True,
            pair_channel: True,
        },
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    from dataclasses import replace

    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta(
    *,
    target_round: int = 0,
    num_steps: int = 5,
    source: str = "flowmol3adapter_test",
    calibration_artifact_hash: str = "cal-flowmol3adapter",
    channel_keys: tuple[str, ...] = (),
) -> ODEConditionDelta:
    spec: dict[str, object] = {"num_steps": int(num_steps)}
    for k in channel_keys:
        spec[k] = "test_delta"
    return ODEConditionDelta(
        delta_spec=spec,
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> FlowMol3V2Adapter:
    """Yield a NumPy-backed :class:`FlowMol3V2Adapter` for tests."""
    return FlowMol3V2Adapter(backend="numpy", num_steps=10)


@pytest.fixture
def initial_bundle(adapter: FlowMol3V2Adapter) -> StateBundle:
    """Build the initial :class:`StateBundle` for ``("b0", "s0")``."""
    return adapter.build_initial_state(batch_id="b0", sample_id="s0")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_capabilities_handshake() -> None:
    """The capability surface advertises the design-spec fields."""
    caps = FlowMol3V2AdapterCapabilities()
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities validation failed: {errs}"
    # design-spec fields
    assert caps.has_ode_integration_surface is True
    assert caps.has_prior_export is True
    assert caps.has_state_export is True
    assert caps.has_condition_injection is False  # unconditional
    assert caps.has_restart_boundary is True
    assert caps.has_continuous_channels is True
    assert caps.has_discrete_channels is True
    assert caps.has_trajectory_digest is True
    assert caps.has_deterministic_seed is True
    assert caps.has_materialization_route is False  # no pocket materialization
    # Channel vocabulary
    assert caps.supported_channels == FLOWMOL3ADAPTER_CHANNELS
    assert tuple(caps.channel_domains.keys()) == FLOWMOL3ADAPTER_CHANNELS
    assert caps.channel_domains == FLOWMOL3ADAPTER_CHANNEL_DOMAINS
    # Native config metadata
    assert caps.native_config_hash == FLOWMOL3ADAPTER_CONFIG_HASH
    assert caps.native_config_version == FLOWMOL3ADAPTER_CONFIG_VERSION
    assert caps.state_shape == FLOWMOL3ADAPTER_STATE_SHAPE


def test_build_initial_state_returns_correct_shape(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """``build_initial_state`` returns a well-formed StateBundle."""
    assert isinstance(initial_bundle, StateBundle)
    # Channels: one TensorRef per supported channel.
    assert set(str(k) for k in initial_bundle.channels.keys()) == set(
        str(k) for k in FLOWMOL3ADAPTER_CHANNELS
    )
    # Validate the bundle.
    ok, errs = validate_state_bundle(initial_bundle)
    assert ok, f"bundle validation failed: {errs}"
    # Detach proof.
    assert initial_bundle.detach_proof is True
    # Source round 0.
    assert initial_bundle.source_round == 0
    # Native state digest is non-empty + deterministic.
    assert initial_bundle.native_state_digest
    # Mask entries are TensorRefs.
    for ch_name in FLOWMOL3ADAPTER_CHANNELS:
        mask_ref = initial_bundle.masks[ch_name]
        # TensorRef is a NewType alias for str; check the underlying type.
        assert isinstance(str(mask_ref), str)
        assert str(mask_ref)
    # Native state entry has the heterogeneous (x, a, c, e) tuple shape.
    native_entry = adapter._native_states[initial_bundle.native_state_digest]
    assert native_entry["x"].shape[1] == 3
    assert native_entry["c"].ndim == 1
    assert native_entry["e"].ndim == 2
    assert native_entry["a"].ndim == 1
    assert native_entry["x"].shape[0] == native_entry["e"].shape[0]
    assert native_entry["x"].shape[0] == native_entry["c"].shape[0]
    assert native_entry["x"].shape[0] == native_entry["a"].shape[0]


def test_solve_ode_returns_finite_trace(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """``solve_ode`` returns a finite trace + stores the lineage."""
    cond = _make_condition_delta(num_steps=5)
    trace = adapter.solve_ode(initial_bundle, cond, seed=42)
    assert isinstance(trace, ODEIntegratorTrace)
    assert trace.steps == 5
    assert 0.0 <= trace.accept_rate <= 1.0
    # Trajectory digest stored under _native_states; check it's there.
    assert trace.native_state_digest in adapter._native_states
    entry = adapter._native_states[trace.native_state_digest]
    assert "traj_x" in entry
    assert "traj_c" in entry
    assert "traj_e" in entry
    assert "traj_a" in entry
    # Trajectory is finite.
    assert np.all(np.isfinite(entry["traj_x"]))
    assert np.all(np.isfinite(entry["traj_c"]))
    # Bond-type labels are in range.
    assert int(entry["traj_e"].max()) < 5
    assert int(entry["traj_e"].min()) >= 0
    # Per-step shape: (num_steps + 1, n_atoms, ...).
    n_atoms = int(entry["n_atoms"])
    assert entry["traj_x"].shape == (6, n_atoms, 3)
    assert entry["traj_c"].shape == (6, n_atoms)
    assert entry["traj_e"].shape == (6, n_atoms, n_atoms)


def test_endpoint_round_trip(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """``observe_endpoint`` returns a bundle whose digest resolves to a state."""
    cond = _make_condition_delta(num_steps=5)
    trace = adapter.solve_ode(initial_bundle, cond, seed=42)
    endpoint = adapter.observe_endpoint(trace, initial_bundle)
    assert isinstance(endpoint, StateBundle)
    assert endpoint.native_state_digest in adapter._native_states
    entry = adapter._native_states[endpoint.native_state_digest]
    # t=1 slice is a (n_atoms, 3) coordinate tensor.
    assert entry["x"].shape[1] == 3
    assert entry["c"].ndim == 1
    assert entry["e"].ndim == 2
    assert entry["a"].ndim == 1
    assert entry["t"] == 1.0
    # Audit code trail includes the trajectory-built marker.
    assert AUDIT_FLOWMOL3_TRAJECTORY_BUILT in entry.get("audit", ())
    # Endpoint bundle increments source_round.
    assert endpoint.source_round == 1
    # Endpoint bundle is detached.
    assert endpoint.detach_proof is True


def test_determinism() -> None:
    """Two adapter instances produce byte-identical digests for identical inputs."""
    a1 = FlowMol3V2Adapter(backend="numpy", num_steps=10)
    a2 = FlowMol3V2Adapter(backend="numpy", num_steps=10)
    b1 = a1.build_initial_state(batch_id="b1", sample_id="s1")
    b2 = a2.build_initial_state(batch_id="b1", sample_id="s1")
    assert b1.native_state_digest == b2.native_state_digest
    # Same digest for solve_ode.
    cond = _make_condition_delta(num_steps=5)
    t1 = a1.solve_ode(b1, cond, seed=99)
    t2 = a2.solve_ode(b2, cond, seed=99)
    assert t1.native_state_digest == t2.native_state_digest


def test_velocity_field_lazy_loads_torch_if_required() -> None:
    """``backend="torch"`` rejects when torch is not installed."""
    # The default NumPy backend does NOT import torch.
    a = FlowMol3V2Adapter(backend="numpy", num_steps=5)
    assert a._model is None  # lazy
    a._velocity_field(
        x=np.zeros((4, 3), dtype=np.float64),
        c=np.zeros((4,), dtype=np.float64),
        e=np.zeros((4, 4), dtype=np.int64),
        t=0.5,
        n_atoms=4,
        seed=0,
    )
    assert a._model is None  # still lazy
    # backend="torch" rejects when torch is not installed (we patch).
    from adaptive_reflow.adapters import flowmol3_v2_adapter as fma

    orig = fma._torch_is_available
    fma._torch_is_available = lambda: False  # type: ignore[assignment]
    try:
        with pytest.raises(ImportError, match="torch backend requested"):
            FlowMol3V2Adapter(backend="torch", num_steps=5)
    finally:
        fma._torch_is_available = orig  # type: ignore[assignment]


def test_restart_blend_channel_aware(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """``apply_restart_distribution`` produces a detached restart bundle."""
    policy = _make_final_policy(beta=0.5)
    next_bundle = adapter.apply_restart_distribution(initial_bundle, policy)
    assert isinstance(next_bundle, StateBundle)
    # Detach proof.
    assert next_bundle.detach_proof is True
    # Source round incremented.
    assert next_bundle.source_round == 1
    # Digest changed.
    assert (
        next_bundle.native_state_digest != initial_bundle.native_state_digest
    )
    # Restart entry stored under the new digest.
    assert next_bundle.native_state_digest in adapter._native_states
    entry = adapter._native_states[next_bundle.native_state_digest]
    # Audit code trail includes the restart-blend marker.
    assert "flowmol3adapter_restart_blend" in entry.get("audit", ())
    # Provenance tag.
    assert AUDIT_FLOWMOL3_RESTART_BLEND in next_bundle.provenance


def test_apply_restart_distribution_happy_path_all_channels(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """Regression — NONCONFORMANCE_BUG #1 happy path.

    With all three FlowMol3 channels present, the channel-set
    pre-validation must NOT short-circuit; the existing 3-channel
    blend math must run and produce a detached restart bundle.
    """
    # Sanity check: the initial bundle carries all 3 channels.
    expected = {
        ChannelName("coordinate"),
        ChannelName("charge"),
        ChannelName("raw_pair"),
    }
    assert set(initial_bundle.channels) == expected

    policy = _make_final_policy(beta=0.5)
    next_bundle = adapter.apply_restart_distribution(initial_bundle, policy)
    assert isinstance(next_bundle, StateBundle)
    assert next_bundle.detach_proof is True
    assert next_bundle.source_round == 1
    assert set(next_bundle.channels) == expected
    # Restart entry stored under the new digest.
    assert next_bundle.native_state_digest in adapter._native_states
    entry = adapter._native_states[next_bundle.native_state_digest]
    assert "flowmol3adapter_restart_blend" in entry.get("audit", ())
    assert AUDIT_FLOWMOL3_RESTART_BLEND in next_bundle.provenance


def test_export_trajectory_returns_lineage(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """``export_trajectory`` returns the per-step (x, a, c, e) lineage."""
    cond = _make_condition_delta(num_steps=5)
    trace = adapter.solve_ode(initial_bundle, cond, seed=42)
    lineage = adapter.export_trajectory(trace)
    assert isinstance(lineage, Mapping)
    assert set(lineage.keys()) == {"traj_x", "traj_c", "traj_e", "traj_a"}
    n_atoms = int(lineage["traj_x"].shape[1])
    assert lineage["traj_x"].shape == (6, n_atoms, 3)
    assert lineage["traj_c"].shape == (6, n_atoms)
    assert lineage["traj_e"].shape == (6, n_atoms, n_atoms)
    assert lineage["traj_a"].shape == (6, n_atoms)
    # Missing digest returns None.
    empty = adapter.export_trajectory(
        ODEIntegratorTrace(
            steps=1,
            accept_rate=1.0,
            native_state_digest="nonexistent-digest",
            integrator_config_hash="dummy-hash",
        )
    )
    assert empty is None


def test_mechanism_id_advertised() -> None:
    """The adapter exposes a writer-authority ``mechanism_id``."""
    a = FlowMol3V2Adapter(backend="numpy", num_steps=5)
    assert a.mechanism_id == FLOWMOL3ADAPTER_MECHANISM_ID


def test_pinned_commit_matches_registry() -> None:
    """The adapter's pinned commit matches the FlowMol3 registry row."""
    a = FlowMol3V2Adapter(backend="numpy", num_steps=5)
    assert a.pinned_commit == FLOWMOL3ADAPTER_PINNED_COMMIT


def test_default_factory() -> None:
    """``default_flowmol3adapter`` returns a fresh adapter."""
    a = default_flowmol3adapter(backend="numpy", num_steps=5)
    assert isinstance(a, FlowMol3V2Adapter)
    assert isinstance(a.capabilities(), AdapterCapabilities)


def test_factory_threads_use_upstream_when_force_mode_real() -> None:
    """Wave 71 Agent 2 — closes GAP-1 (Wave 70 Phase 1 audit §1.8).

    When ``force_mode in {"real", "auto"}`` the factory MUST thread
    ``use_upstream=True`` to ``FlowMol3V2Adapter(...)`` so the real
    FlowMol3 ckpt forward is taken (instead of the partial-fidelity
    fallback). Without this plumbing the ``solve_ode`` upstream
    branch at ``flowmol3_v2_adapter.py:2253`` is dead code in
    practice.
    """
    for force_mode in ("real", "auto"):
        a = default_flowmol3adapter(
            backend="torch",
            num_steps=5,
            device="cpu",
            force_mode=force_mode,
        )
        assert isinstance(a, FlowMol3V2Adapter)
        # The ``use_upstream`` property reflects the constructor
        # flag — the integration test below verifies the flag was
        # actually set, not silently defaulted.
        assert a.use_upstream is True, (
            f"force_mode={force_mode!r} must yield use_upstream=True"
        )


def test_factory_preserves_use_upstream_false_when_force_mode_synthetic() -> None:
    """Wave 71 Agent 2 — backward-compat (byte-stability contract).

    When ``force_mode in {None, "synthetic"}`` the factory MUST keep
    the legacy ``use_upstream=False`` default. This preserves the
    synthetic-mode verdict (composite=0.0 + marker="synthetic_fallback")
    and the D.4 byte-stable regression vectors.
    """
    for force_mode in (None, "synthetic"):
        a = default_flowmol3adapter(
            backend="numpy",
            num_steps=5,
            force_mode=force_mode,
        )
        assert isinstance(a, FlowMol3V2Adapter)
        assert a.use_upstream is False, (
            f"force_mode={force_mode!r} must yield use_upstream=False "
            "(byte-stability contract)"
        )

