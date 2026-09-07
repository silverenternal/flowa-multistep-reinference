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


def test_protocol_conformance() -> None:
    """The adapter passes the @runtime_checkable Protocol isinstance check."""
    a = FlowMol3V2Adapter(backend="numpy", num_steps=5)
    assert isinstance(a, FlowMatchingODEAdapter)
    # Required methods present.
    for name in (
        "capabilities",
        "build_initial_state",
        "export_endpoint",
        "detach_and_validate_endpoint",
        "apply_restart_distribution",
        "compose_condition",
        "solve_ode",
        "observe_endpoint",
        "export_trajectory",
    ):
        assert hasattr(a, name), f"missing method: {name}"


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


def test_apply_restart_distribution_rejects_missing_channel_with_clear_error(
    adapter: FlowMol3V2Adapter,
) -> None:
    """Regression — NONCONFORMANCE_BUG #1.

    A state bundle that is missing one or more of the three
    FlowMol3 channels (``coordinate``, ``charge``, ``raw_pair``)
    must raise a clear :class:`ValueError` rather than crashing
    deep inside the blend math with an opaque shape-mismatch
    error.
    """
    # Build a bundle that only carries the ``coordinate`` channel.
    partial_bundle = adapter.build_initial_state(batch_id="b1", sample_id="s1")
    partial_bundle = StateBundle(
        channels={ChannelName("coordinate"): partial_bundle.channels[ChannelName("coordinate")]},
        masks={ChannelName("coordinate"): partial_bundle.masks[ChannelName("coordinate")]},
        batch_id=partial_bundle.batch_id,
        sample_id=partial_bundle.sample_id,
        reference_frame=partial_bundle.reference_frame,
        normalization=partial_bundle.normalization,
        source_round=partial_bundle.source_round,
        detach_proof=partial_bundle.detach_proof,
        native_state_digest=partial_bundle.native_state_digest,
        provenance=partial_bundle.provenance,
        capability_token=partial_bundle.capability_token,
    )
    policy = _make_final_policy(beta=0.5)
    with pytest.raises(ValueError, match=r"missing channels"):
        adapter.apply_restart_distribution(partial_bundle, policy)


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


def test_compose_condition_rejects_channel_keys(
    adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
) -> None:
    """``compose_condition`` rejects channel-keyed deltas (unconditional)."""
    # Empty delta: pass-through (configurable keys like num_steps OK).
    delta = _make_condition_delta(channel_keys=())
    out = adapter.compose_condition(initial_bundle, delta)
    assert isinstance(out, ODEConditionDelta)
    assert out.delta_spec["num_steps"] == 5
    # Non-empty channel-keyed delta: rejected with CapabilityMissingError.
    delta_bad = _make_condition_delta(channel_keys=("coordinate",))
    with pytest.raises(CapabilityMissingError) as exc:
        adapter.compose_condition(initial_bundle, delta_bad)
    assert exc.value.capability == "has_condition_injection"


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


# ---------------------------------------------------------------------------
# Wave 70 Phase 3 — :meth:`FlowMol3V2Adapter.export_sampled_molecules`
# decodes the cached trajectory to ``list[RDKit Mol]`` + metadata.
#
# The method is OPT-IN (default behaviour unchanged) and graceful on
# placeholder / synthetic entries. Closes the Wave 70 Phase 1 GAP-2
# audit finding.
# ---------------------------------------------------------------------------


class TestFlowMol3V2ExportSampledMolecules:
    """``export_sampled_molecules(trace)`` decodes trajectory to RDKit Mol.

    Wave 70 Phase 3 close-out. The eval pipeline
    ``_compute_flowmol3_composite`` consumes a sequence of upstream
    ``SampledMolecule`` objects (or any object accepted by upstream
    ``SampleAnalyzer.analyze``). The v2 adapter's :meth:`export_trajectory`
    only returns raw (x, a, c, e) arrays — this method bridges the gap
    by decoding the endpoint slice to RDKit ``Mol`` objects.
    """

    def test_export_sampled_molecules_returns_list_of_mols(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        """On a real (synthetic-but-completed) forward the method decodes to a Mol.

        The NumPy backend runs ``_solve_ode_linear`` so the cached
        trajectory is the per-step heterogeneous (x, a, c, e) lineage.
        The decoder walks ``traj_a[-1]`` / ``traj_e[-1]`` /
        ``traj_x[-1]`` and constructs an RDKit ``Mol`` with a 3D
        conformer. The list length is 1 (single-molecule batch on v2).

        Note: the synthetic ``_solve_ode_linear`` trajectory is NOT
        a chemically-valid molecule (random atom-types + bond-types).
        RDKit sanitize therefore fails; the decoder returns
        ``marker='ok_partial'`` with a structurally-reconstructed
        ``Mol`` (no valence check). Real ckpt forward path uses the
        upstream SMILES shortcut (``marker='ok'``).
        """
        cond = _make_condition_delta(num_steps=5)
        trace = adapter.solve_ode(initial_bundle, cond, seed=42)
        mols, meta = adapter.export_sampled_molecules(trace)
        assert isinstance(mols, list)
        assert len(mols) == 1
        mol = mols[0]
        # RDKit ``Mol`` duck-type: has ``GetNumAtoms`` + ``GetNumBonds``.
        assert hasattr(mol, "GetNumAtoms")
        assert hasattr(mol, "GetNumBonds")
        assert int(mol.GetNumAtoms()) > 0
        # Metadata echo.
        assert isinstance(meta, Mapping)
        # Synthetic path -> 'ok_partial'; upstream SMILES path -> 'ok'.
        assert meta.get("marker") in ("ok", "ok_partial")
        assert meta.get("sanitize_status") in ("ok", "ok_partial")
        assert int(meta.get("n_atoms", -1)) == int(mol.GetNumAtoms())
        assert int(meta.get("n_bonds", -1)) == int(mol.GetNumBonds())
        assert int(meta.get("build_errors", -1)) == 0
        assert meta.get("smiles", "") != ""

    def test_export_sampled_molecules_placeholder_returns_empty(
        self, adapter: FlowMol3V2Adapter
    ) -> None:
        """A missing digest returns ``([], {marker=no_lineage})`` (graceful)."""
        empty_trace = ODEIntegratorTrace(
            steps=1,
            accept_rate=1.0,
            native_state_digest="nonexistent-digest",
            integrator_config_hash="dummy-hash",
        )
        mols, meta = adapter.export_sampled_molecules(empty_trace)
        assert mols == []
        assert isinstance(meta, Mapping)
        assert meta.get("marker") == "no_lineage"
        assert int(meta.get("n_atoms", -1)) == 0
        assert int(meta.get("n_bonds", -1)) == 0

    def test_export_sampled_molecules_handles_3d_coords(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        """The decoded Mol carries a 3D conformer with the endpoint positions."""
        cond = _make_condition_delta(num_steps=5)
        trace = adapter.solve_ode(initial_bundle, cond, seed=42)
        mols, _meta = adapter.export_sampled_molecules(trace)
        assert len(mols) == 1
        mol = mols[0]
        # RDKit exposes the conformer with ``GetConformer`` (3D).
        conf = mol.GetConformer()
        assert conf.Is3D() is True
        n_atoms = int(mol.GetNumAtoms())
        assert n_atoms > 0
        # Position lookup must succeed for every atom (smoke check on
        # the conformer layout).
        positions = [tuple(conf.GetAtomPosition(i)) for i in range(n_atoms)]
        assert len(positions) == n_atoms
        # All positions are finite floats.
        for (xx, yy, zz) in positions:
            assert isinstance(xx, float)
            assert isinstance(yy, float)
            assert isinstance(zz, float)

    def test_export_sampled_molecules_byte_stable(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        """``export_trajectory`` return value is unchanged after the addition.

        Two adapter instances with identical seeds must return
        byte-identical lineage dicts. The D.4 regression contract is
        that the new method is OPT-IN — calling :meth:`export_sampled_molecules`
        does not mutate the cached entry, so a subsequent call to
        :meth:`export_trajectory` returns the same lineage as the
        first call.
        """
        cond = _make_condition_delta(num_steps=5)
        trace = adapter.solve_ode(initial_bundle, cond, seed=42)
        # First export — pre-sampled-molecules.
        lineage_before = adapter.export_trajectory(trace)
        assert lineage_before is not None
        # Trigger the new method (consumes the lineage but does not mutate).
        mols, meta = adapter.export_sampled_molecules(trace)
        assert len(mols) == 1
        # Synthetic data may produce 'ok_partial' (synthetic valences
        # are not chemically valid). Upstream SMILES path produces 'ok'.
        assert meta.get("marker") in ("ok", "ok_partial")
        # Re-export — must be byte-identical (no mutation).
        lineage_after = adapter.export_trajectory(trace)
        assert lineage_after is not None
        for key in ("traj_x", "traj_c", "traj_e", "traj_a"):
            assert np.array_equal(lineage_before[key], lineage_after[key]), (
                f"export_trajectory[{key!r}] mutated by export_sampled_molecules"
            )
        # And: two adapters with identical inputs → byte-identical digests
        # (the canonical D.4 byte-stability check from Wave 49/50).
        a2 = FlowMol3V2Adapter(backend="numpy", num_steps=5)
        b2 = a2.build_initial_state(batch_id="b0", sample_id="s0")
        t2 = a2.solve_ode(b2, cond, seed=42)
        assert t2.native_state_digest == trace.native_state_digest


# ---------------------------------------------------------------------------
# Wave 68 Phase 3 — :meth:`FlowMol3V2Adapter.observe` closes the Wave 66
# v2 wire gap (``adapter_missing_observe_entropy_reduction`` BLOCKED).
# ---------------------------------------------------------------------------


class TestFlowMol3V2ObserveProtocol:
    """``observe(...)`` returns a typed tuple tagged by :class:`ObservationKind`.

    The v2 adapter supports ``ENDPOINT_BUNDLE`` (per-channel
    endpoint) and ``POSITION_ENTROPY_REDUCTION`` (per-atom atom-type
    entropy reduction derived from the cached ``traj_a`` lineage).
    The new ``POSITION_ENTROPY_REDUCTION`` strategy closes the Wave
    66 v2 wire gap: the eval pipeline
    ``_compute_flowmol3_real_metric_via_trace`` no longer hits
    ``adapter_missing_observe_entropy_reduction`` for v2 real-ckpt
    cells.
    """

    def _make_adapter_with_trace(self, num_steps: int = 3):
        """Construct adapter, run ``solve_ode``, return ``(adapter, trace, state)``."""
        adapter = default_flowmol3adapter(
            backend="numpy", num_steps=num_steps
        )
        state = adapter.build_initial_state(
            batch_id="b", sample_id="s"
        )
        cond = ODEConditionDelta(
            delta_spec={"num_steps": int(num_steps)},
            source="test_flowmol3v2_observe",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(state, cond, seed=0)
        return adapter, trace, state

    def test_observe_conforms_to_protocol(self) -> None:
        """``observe(...)`` satisfies the :class:`AdapterObservationProtocol` Protocol."""
        from adaptive_reflow.framework.interfaces import AdapterObservationProtocol
        adapter = default_flowmol3adapter(backend="numpy", num_steps=2)
        assert isinstance(adapter, AdapterObservationProtocol)

    def test_observe_default_returns_two_results(self) -> None:
        """Default strategies → ``ENDPOINT_BUNDLE`` + ``POSITION_ENTROPY_REDUCTION``."""
        from adaptive_reflow.framework.interfaces import ObservationKind
        adapter, trace, state = self._make_adapter_with_trace(num_steps=3)
        results = adapter.observe(trace, state)
        kinds = {r.kind for r in results}
        assert kinds == {
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
        }
        assert len(results) == 2

    def test_observe_entropy_shim_uses_cached_traj_a(self) -> None:
        """Entropy shim derives ``theta_after`` from the cached ``traj_a`` lineage.

        Closes the Wave 66 BLOCKED failure mode: when the eval
        pipeline passes only ``theta_before`` (or nothing), the
        adapter's cached ``traj_a[-1]`` integer labels are turned
        into a softmax-normalised marginal and the entropy
        reduction is computed via the shared
        :func:`per_position_entropy_reduction` helper.
        """
        import numpy as np

        from adaptive_reflow.framework.interfaces import ObservationKind

        adapter, trace, state = self._make_adapter_with_trace(num_steps=3)
        results = adapter.observe(
            trace,
            state,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        assert len(results) == 1
        result = results[0]
        assert result.kind == ObservationKind.POSITION_ENTROPY_REDUCTION
        assert result.units == "nats"
        # theta_after_source must be the entropy shim, not explicit.
        assert result.metadata["theta_after_supplied"] is False
        assert result.metadata["theta_after_source"] in (
            "traj_a_one_hot_softmax",
            "uniform_fallback",
        )
        # Payload is a float (reduction in nats) — finite number.
        assert isinstance(result.payload, float)
        assert np.isfinite(result.payload)

    def test_observe_with_explicit_theta_arrays(self) -> None:
        """Explicit ``theta_before`` + ``theta_after`` produce a meaningful reduction."""
        import numpy as np

        from adaptive_reflow.framework.interfaces import ObservationKind

        adapter, trace, state = self._make_adapter_with_trace(num_steps=3)
        theta_after = np.zeros(
            (8, int(FLOWMOL3ADAPTER_N_ATOM_TYPES)), dtype=np.float64
        )
        theta_after[:, 0] = 100.0  # confident spike
        theta_before = np.full_like(theta_after, 1.0)  # uniform
        results = adapter.observe(
            trace,
            state,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
            theta_before=theta_before,
            theta_after=theta_after,
        )
        assert len(results) == 1
        result = results[0]
        # Sharpened after-vs-uniform before → positive reduction.
        assert result.payload > 0.0
        assert result.metadata["theta_before_supplied"] is True
        assert result.metadata["theta_after_supplied"] is True

    def test_observe_byte_stable_across_calls(self) -> None:
        """Two calls with the same (adapter, trace, state) return identical results."""
        from adaptive_reflow.framework.interfaces import ObservationKind

        adapter, trace, state = self._make_adapter_with_trace(num_steps=3)
        r1 = adapter.observe(
            trace,
            state,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        r2 = adapter.observe(
            trace,
            state,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        # The metadata dict is excluded from __eq__ (debug-only) but
        # the payload + kind + units are stable.
        assert r1[0].kind == r2[0].kind
        assert r1[0].units == r2[0].units
        assert r1[0].payload == r2[0].payload

    def test_observe_legacy_endpoint_still_works(self) -> None:
        """The legacy :meth:`observe_endpoint` is preserved byte-identically."""
        adapter, trace, state = self._make_adapter_with_trace(num_steps=3)
        ep = adapter.observe_endpoint(trace, state)
        # Byte-stable surface: same fields as before Wave 68 Phase 3.
        assert hasattr(ep, "native_state_digest")
        assert ep.source_round == state.source_round + 1
        assert "flowmol3adapter_observed" in ep.provenance

    def test_observe_with_state_none_returns_entropy_only(self) -> None:
        """Regression (Wave 68 closure): ``state=None`` must not crash.

        The metric helper ``_extract_observation`` in
        ``tools/run_real_ckpt_eval.py`` historically passes ``state=None``
        to ``adapter.observe(...)``. The Wave 68 Phase 4 refactor of
        ``_compute_real_metric_via_observation`` made this the default
        for all 4 model paths. The Wave 54 Phase 2 Fix (commit
        ``223a225``) added the defensive ``state is not None`` guard in
        the ``observe()`` callee side so the POSITION_ENTROPY_REDUCTION
        shim can still produce a finite number via the trajectory-only
        fallback when ``state`` is ``None``.
        """
        import numpy as np

        from adaptive_reflow.framework.interfaces import ObservationKind

        adapter, trace, _ = self._make_adapter_with_trace(num_steps=3)
        results = adapter.observe(
            trace,
            None,                                          # state=None
            paper_quantities=None,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        assert len(results) == 1
        result = results[0]
        assert result.kind == ObservationKind.POSITION_ENTROPY_REDUCTION
        assert isinstance(result.payload, float)
        assert np.isfinite(result.payload)

    def test_observe_as_dict_with_state_none_returns_entropy_kind(self) -> None:
        """Regression (Wave 68 closure): ``observe_as_dict(..., state=None)`` is safe.

        The metric helper's observe_as_dict branch (line 1597 of
        ``tools/run_real_ckpt_eval.py``) calls this method with
        ``state=None``. The Wave 54 Phase 2 Fix (commit ``223a225``)
        added a defensive guard at the callee side so ENDPOINT_BUNDLE
        is dropped from the requested strategies when ``state is None``
        and POSITION_ENTROPY_REDUCTION still produces a finite number.
        """
        import numpy as np

        from adaptive_reflow.framework.interfaces import ObservationKind

        adapter, trace, _ = self._make_adapter_with_trace(num_steps=3)
        obs_dict = adapter.observe_as_dict(
            trace,
            None,                                          # state=None
            paper_quantities=None,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        # ENDPOINT_BUNDLE is dropped when state is None (callee guard).
        assert obs_dict[ObservationKind.ENDPOINT_BUNDLE] is None
        # POSITION_ENTROPY_REDUCTION still produces a finite number.
        entropy = obs_dict[ObservationKind.POSITION_ENTROPY_REDUCTION]
        assert entropy is not None
        assert isinstance(entropy.payload, float)
        assert np.isfinite(entropy.payload)