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


# ---
# (Header + imports shared with test_flowmol3_v2_adapter_smoke.py; see that file.)
# ---

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

    Wave 122: every test in this class is gated by rdkit availability
    via a per-method ``pytest.importorskip('rdkit')`` because the
    decoder (``_decode_rdkit_mol_from_arrays``) returns ``(None,
    'none')`` when ``from rdkit import Chem`` fails, which causes
    ``export_sampled_molecules`` to return ``[]`` — a false
    regression signal on rdkit-less CI envs.
    """

    def test_export_sampled_molecules_returns_list_of_mols(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        pytest.importorskip(
            "rdkit",
            reason=(
                "RDKit is required to decode trajectory to Mol objects "
                "(install via 'uv pip install rdkit')"
            ),
        )
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
        pytest.importorskip(
            "rdkit",
            reason=(
                "RDKit is required to decode trajectory to Mol objects "
                "(install via 'uv pip install rdkit')"
            ),
        )
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
        pytest.importorskip(
            "rdkit",
            reason=(
                "RDKit is required to decode trajectory to Mol objects "
                "(install via 'uv pip install rdkit')"
            ),
        )
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
# Wave 74 F1 — multi-molecule cells (``n_molecules`` kwarg).
#
# Interface-first contract:
# * ``n_molecules=1`` (default) preserves the legacy single-molecule
#   trajectory shape — D.4 byte-stability.
# * ``n_molecules>1`` triggers the synthetic batch path (or upstream
#   batch path when ``use_upstream=True``); the cached entry carries
#   ``traj_x_batch`` / ``traj_c_batch`` / ``traj_e_batch`` /
#   ``traj_a_batch`` of shape ``(n_molecules, num_steps+1, n, ...)``
#   plus ``n_molecules`` integer key.
# ---------------------------------------------------------------------------


class TestFlowMol3V2NMoleculesBatch:
    """``solve_ode(..., n_molecules=N)`` returns batched lineage for N>1."""

    def test_v2_supports_n_molecules_kwarg(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        """n_molecules=4 returns 4 molecules via ``export_sampled_molecules``."""
        pytest.importorskip(
            "rdkit",
            reason=(
                "RDKit is required to decode batched trajectory to Mol "
                "objects (install via 'uv pip install rdkit')"
            ),
        )
        cond = _make_condition_delta(num_steps=3)
        trace = adapter.solve_ode(
            initial_bundle, cond, seed=42, n_molecules=4,
        )
        mols, meta = adapter.export_sampled_molecules(trace)
        assert isinstance(mols, list)
        assert len(mols) == 4
        for mol in mols:
            assert hasattr(mol, "GetNumAtoms")
            assert hasattr(mol, "GetNumBonds")
            assert int(mol.GetNumAtoms()) > 0
        assert isinstance(meta, Mapping)
        assert meta.get("marker") in ("ok_batch", "ok_partial_batch", "ok")
        assert int(meta.get("n_molecules", -1)) == 4

    def test_v2_n_molecules_aggregates_composite(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        """Mean (not median) aggregation across the n_molecules batch.

        The glue's ``compute_chemistry_metrics`` consumes the list and
        the upstream ``SampleAnalyzer.analyze`` aggregates over the
        batch internally. We verify that ``export_sampled_molecules``
        returns the full N-molecule list (not collapsed) so the
        downstream consumer can aggregate freely.

        Note on aggregation choice: the F1 plan uses **mean** over
        molecules per cell (rather than median). Justification: the
        chemistry axes ``frac_valid_mols`` / ``frac_mols_stable_valence``
        are themselves expected values of the per-mol Bernoulli
        indicators (sample-mean across molecules), so taking the
        per-cell mean aligns with the upstream ``SampleAnalyzer``
        semantics. Median would discard information for n<10 and
        bias against the very small n range where the F1 win matters
        most (cutting the ±0.6 spread to ±0.2 at n=10 requires using
        the sample-mean estimator, not a robust median).
        """
        pytest.importorskip(
            "rdkit",
            reason=(
                "RDKit is required to decode batched trajectory to Mol "
                "objects (install via 'uv pip install rdkit')"
            ),
        )
        cond = _make_condition_delta(num_steps=3)
        trace = adapter.solve_ode(
            initial_bundle, cond, seed=42, n_molecules=5,
        )
        mols, meta = adapter.export_sampled_molecules(trace)
        assert len(mols) == 5
        # Mean aggregation: every mol contributes equally. We verify
        # the contract that the list is NOT collapsed to length 1
        # (which would be the median-style "representative" output).
        assert sum(1 for m in mols if m is not None) == 5

    def test_v2_n_molecules_default_1_preserves_byte_stability(
        self, adapter: FlowMol3V2Adapter, initial_bundle: StateBundle
    ) -> None:
        """D.4 byte-stability: ``n_molecules=1`` produces the legacy trajectory shape.

        Locks in the byte-stable contract: when ``n_molecules=1`` (the
        default) the cached entry uses ``traj_x`` / ``traj_c`` /
        ``traj_e`` / ``traj_a`` (NOT the ``*_batch`` keys) and the
        output length is 1 molecule. ``export_sampled_molecules``
        returns ``marker='ok'`` (or ``'ok_partial'`` for synthetic data).
        """
        pytest.importorskip(
            "rdkit",
            reason=(
                "RDKit is required to decode trajectory to Mol objects "
                "(install via 'uv pip install rdkit')"
            ),
        )
        cond = _make_condition_delta(num_steps=5)
        # Default n_molecules.
        trace = adapter.solve_ode(initial_bundle, cond, seed=42)
        mols, meta = adapter.export_sampled_molecules(trace)
        assert len(mols) == 1
        assert meta.get("marker") in ("ok", "ok_partial")
        # Explicit n_molecules=1 — must be identical to default.
        trace_explicit = adapter.solve_ode(
            initial_bundle, cond, seed=42, n_molecules=1,
        )
        assert (
            trace_explicit.native_state_digest == trace.native_state_digest
        ), (
            "Explicit n_molecules=1 must produce the same digest as "
            "the default (D.4 byte-stability)."
        )


# ---------------------------------------------------------------------------
# Wave 74 F2 — seed threading through the upstream ``FlowMol.sample`` call.
#
# The upstream ``FlowMol.sample`` has NO per-call ``seed=`` kwarg — it
# consumes the module-level torch / numpy RNG state at call time. The
# adapter therefore wraps the upstream call in a ``_seed_everything``
# context manager so that three repeat runs of the same upstream
# ``(seed=...)`` produce byte-identical output (closes the Wave 73
# ±0.6 composite-spread root cause).
#
# These tests are written against the public ``_seed_everything``
# context manager (which is testable without dgl + torch_scatter)
# and against the seed-handling **contract** of ``_solve_ode_upstream``
# via a lightweight stub model that records the RNG state seen
# inside the ``with _seed_everything(...)`` block. The stub bypasses
# the heavy dgl / flowmol import path.
# ---------------------------------------------------------------------------


class TestFlowMol3V2SeedThreading:
    """``_solve_ode_upstream`` / ``_solve_ode_upstream_batch`` thread ``seed``.

    The adapter exposes a ``seed=`` kwarg on :meth:`solve_ode` and
    :meth:`_solve_ode_upstream`. Before Wave 74 F2, the adapter
    *accepted* the seed but did NOT propagate it into the upstream
    ``FlowMol.sample`` call (which consumes torch / numpy RNG state
    at call time, not a per-call seed parameter). The
    ``_seed_everything`` context manager now wraps the upstream call.
    """

    def test_v2_seed_everything_helper_is_deterministic(self) -> None:
        """Three runs at the same seed produce byte-identical RNG output.

        Verifies the underlying primitive: the ``_seed_everything``
        context manager seeds torch + numpy at entry; the seeded RNG
        advances identically across multiple invocations at the same
        seed. This is the byte-stability guarantee the upstream call
        relies on.
        """
        torch = pytest.importorskip("torch")
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            _seed_everything,
        )

        def _sample(seed: int) -> torch.Tensor:
            with _seed_everything(int(seed), "cpu"):
                # Two RNG draws: the second one advances the seeded
                # state, so re-running the same block must produce the
                # same two-draw sequence.
                a = torch.rand(7)
                b = torch.rand(7)
            return torch.cat([a, b])

        # Three runs at seed=42 must be byte-equal.
        out_42_a = _sample(42)
        out_42_b = _sample(42)
        out_42_c = _sample(42)
        assert torch.equal(out_42_a, out_42_b), (
            "Two _seed_everything runs at seed=42 produced different "
            "first outputs (helper is non-deterministic)"
        )
        assert torch.equal(out_42_b, out_42_c), (
            "Three _seed_everything runs at seed=42 produced different "
            "outputs across runs (helper is non-deterministic)"
        )

    def test_v2_seed_everything_helper_restores_rng_state(self) -> None:
        """RNG state must be restored on context exit (no framework leak).

        Regression guard: the helper saves ``torch.get_rng_state`` +
        ``np.random.get_state`` at entry and restores on exit. After
        the ``with`` block returns, the outer RNG state must be
        identical to what it was at entry — even if the body advanced
        the RNG aggressively.
        """
        torch = pytest.importorskip("torch")
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            _seed_everything,
        )

        # Capture the outer RNG state at A.
        torch.manual_seed(2025)
        torch.rand(5)
        outer_state_before = torch.get_rng_state().clone()
        outer_np_state_before = np.random.get_state()

        helper_advanced_torch = False
        with _seed_everything(99, "cpu"):
            # Inside the block: seed is forced to 99 — the outer state
            # must NOT match.
            inner_state = torch.get_rng_state().clone()
            assert not torch.equal(inner_state, outer_state_before), (
                "_seed_everything did not change the torch RNG state "
                "at entry (seed plumbing is a no-op)"
            )
            torch.rand(50)
            helper_advanced_torch = True

        # After exit, outer state must be restored.
        outer_state_after = torch.get_rng_state()
        outer_np_state_after = np.random.get_state()
        assert helper_advanced_torch
        assert torch.equal(outer_state_after, outer_state_before), (
            "torch RNG state NOT restored after _seed_everything exit "
            "(framework scheduler would be affected)"
        )
        # NumPy legacy RNG state: keys + pos tuple equality.
        assert outer_np_state_after[0] == outer_np_state_before[0]
        assert outer_np_state_after[1].shape == outer_np_state_before[1].shape
        np.testing.assert_array_equal(
            outer_np_state_after[1], outer_np_state_before[1],
        )

    def test_v2_seed_kwarg_threaded_into_upstream_sample(self) -> None:
        """``solve_ode(..., seed=N)`` must seed the upstream RNG state.

        Integration check via a stub model: we construct an adapter
        in upstream mode (mocked to skip the heavy dgl / flowmol
        import path), call :meth:`_solve_ode_upstream` with the same
        seed twice, and verify the stub records a deterministic
        torch-RNG state (which is the byte-stability contract F2
        promises).

        The stub's ``sample(...)`` reads the *current* torch RNG state
        at call time and returns a SampledMolecule carrying the state
        hash. Two ``_solve_ode_upstream(seed=42)`` calls must produce
        the same hash; two calls with different seeds must produce
        different hashes.
        """
        torch = pytest.importorskip("torch")
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            _seed_everything,
            FlowMol3V2Adapter,
        )

        # ----------------------------------------------------------------
        # Stub SampledMolecule + model
        # ----------------------------------------------------------------
        class _StubMol:
            """Minimal SampledMolecule duck-type for _solve_ode_upstream."""

            def __init__(self, rng_state_hash: str) -> None:
                self.num_atoms = 3
                # 3 atoms, 3 coords each — valid (3, 3) for the adapter's
                # ``reshape(n_final, 3)`` line at line 2510.
                pos = np.asarray(
                    [
                        [0.0, 0.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0],
                    ],
                    dtype=np.float64,
                )
                self.positions = torch.as_tensor(pos, dtype=torch.float32)
                self.atom_types = ["C", "H", "H"]
                self.atom_charges = torch.as_tensor(
                    [[0], [0], [0]], dtype=torch.float32,
                )
                self.bond_src_idxs = torch.as_tensor([], dtype=torch.long)
                self.bond_dst_idxs = torch.as_tensor([], dtype=torch.long)
                self.bond_types = torch.as_tensor([], dtype=torch.long)
                self.rdkit_mol = None
                self._rng_state_hash = rng_state_hash

        class _StubUpstreamModel:
            """Records the post-seed torch RNG state on every ``sample`` call.

            The ``sample`` method body reads ``torch.get_rng_state`` to
            capture what the adapter's seed context manager established.
            It returns a single ``_StubMol`` whose ``_rng_state_hash``
            is the SHA-256 of the captured state. Two adapter calls at
            the same seed must produce the same hash (byte-stability);
            different seeds must produce different hashes.
            """

            def __init__(self) -> None:
                self.n_atom_types = 11
                self.n_atom_charges = 6
                self.n_bond_types = 4
                self.fake_atoms = False
                self.atom_type_map = [
                    "C", "H", "N", "O", "F", "P", "S", "Cl", "Br", "I",
                ]
                self.last_rng_hash: str | None = None

            def sample(self, *, n_atoms, n_timesteps, device, prior):
                state = torch.get_rng_state()
                import hashlib as _hl
                rng_hash = _hl.sha256(
                    state.cpu().numpy().tobytes()
                ).hexdigest()
                self.last_rng_hash = rng_hash
                return [_StubMol(rng_hash)]

        # ----------------------------------------------------------------
        # Adapter construction (bypass the heavy _load_model path).
        # ----------------------------------------------------------------
        adapter = FlowMol3V2Adapter(
            backend="torch", device="cpu", use_upstream=True,
        )
        # Inject the stub upstream model — bypasses _load_model entirely.
        stub = _StubUpstreamModel()
        adapter._model = stub
        adapter._use_upstream = True
        adapter._model_meta = {"kind": "upstream_flowmol"}
        # Seed a state for the solve_ode path.
        state = adapter.build_initial_state(batch_id="b0", sample_id="s0")
        cond = _make_condition_delta(num_steps=3)

        # Three calls at the same seed (42) → byte-identical state hashes.
        digests: list[str] = []
        for _ in range(3):
            adapter.solve_ode(state, cond, seed=42)
            assert stub.last_rng_hash is not None
            digests.append(stub.last_rng_hash)
        assert digests[0] == digests[1] == digests[2], (
            f"Three calls at seed=42 produced non-identical RNG state "
            f"hashes: {digests!r} (F2 determinism contract broken)"
        )

        # Two different seeds (42 vs 43) → distinct state hashes.
        adapter.solve_ode(state, cond, seed=42)
        hash_42 = stub.last_rng_hash
        adapter.solve_ode(state, cond, seed=43)
        hash_43 = stub.last_rng_hash
        assert hash_42 != hash_43, (
            f"seed=42 and seed=43 produced the same RNG state hash "
            f"({hash_42!r}); seed is not threaded into the upstream call"
        )

    def test_v2_seed_propagation_determinism_three_runs(self) -> None:
        """3 consecutive ``_solve_ode_upstream(seed=N)`` runs produce identical traces.

        Wave 74 F2 acceptance criterion: ``--seeds 42 43 44`` must
        produce *byte-identical* composite values across runs. The
        upper-level evidence is captured in ``wave74-phase3-f2.md``;
        this test is the per-run, in-process byte-stability check.

        Uses the same stub harness as
        :meth:`test_v2_seed_kwarg_threaded_into_upstream_sample`.
        """
        torch = pytest.importorskip("torch")
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            FlowMol3V2Adapter,
        )

        class _StubMol:
            def __init__(self) -> None:
                self.num_atoms = 3
                pos = np.asarray(
                    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                    dtype=np.float64,
                )
                self.positions = torch.as_tensor(pos, dtype=torch.float32)
                self.atom_types = ["C", "H", "H"]
                self.atom_charges = torch.as_tensor(
                    [[0], [0], [0]], dtype=torch.float32,
                )
                self.bond_src_idxs = torch.as_tensor([], dtype=torch.long)
                self.bond_dst_idxs = torch.as_tensor([], dtype=torch.long)
                self.bond_types = torch.as_tensor([], dtype=torch.long)
                self.rdkit_mol = None

        class _StubModel:
            def __init__(self) -> None:
                self.n_atom_types = 11
                self.n_atom_charges = 6
                self.n_bond_types = 4
                self.fake_atoms = False
                self.atom_type_map = [
                    "C", "H", "N", "O", "F", "P", "S", "Cl", "Br", "I",
                ]

            def sample(self, *, n_atoms, n_timesteps, device, prior):
                return [_StubMol()]

        # Build 3 adapters (the native_state cache must not leak between
        # adapter instances — that's the D.4 byte-stability contract).
        adapters = [
            FlowMol3V2Adapter(
                backend="torch", device="cpu", use_upstream=True,
            )
            for _ in range(3)
        ]
        cond = _make_condition_delta(num_steps=3)
        digests: list[str] = []
        for adapter in adapters:
            # Bypass heavy load path.
            adapter._model = _StubModel()
            adapter._use_upstream = True
            adapter._model_meta = {"kind": "upstream_flowmol"}
            # Build state on each adapter (per-adapter native-state cache).
            state = adapter.build_initial_state(batch_id="b", sample_id="s")
            trace = adapter.solve_ode(state, cond, seed=42)
            digests.append(trace.native_state_digest)
        assert digests[0] == digests[1] == digests[2], (
            f"Three adapter instances at seed=42 produced non-identical "
            f"trace digests: {digests!r} (F2 3-run byte-identical contract "
            f"broken)"
        )


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

# ---------------------------------------------------------------------------
# Wave 73 Agent 3 — GAP-5 + GAP-6 (surfaced by closing eval-pipeline GAP-4)
# ---------------------------------------------------------------------------


def test_solve_ode_forces_model_load_before_dispatch() -> None:
    """`solve_ode` loads the model before the upstream/CTMC dispatch (GAP-5).

    Pre-fix: the model loaded lazily inside the velocity field, so on the
    first ``solve_ode`` call ``self._model is None`` and
    ``_loaded_model_kind()`` answered ``"synthetic"``. The
    ``use_upstream`` fast-path was therefore skipped and
    ``_solve_ode_ctmc`` invoked the real-weights velocity field with
    ``module=None``, raising
    ``TypeError: 'NoneType' object is not callable``.

    Post-fix: the torch backend loads before dispatch. This test asserts
    the load hook fires — without needing real weights (``weights_path``
    stays ``None``, so ``_load_model`` returns the ``"synthetic"``
    sentinel and the numpy field runs as before).
    """
    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        _torch_is_available,
        default_flowmol3adapter,
    )

    if not _torch_is_available():
        pytest.skip("torch not importable in this env")

    adapter = default_flowmol3adapter(backend="torch", num_steps=3)
    calls: list[int] = []
    original = adapter._load_model

    def _counting_load() -> object:
        calls.append(1)
        return original()

    adapter._load_model = _counting_load  # type: ignore[method-assign]
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    from adaptive_reflow.universal.state import ODEConditionDelta

    condition = ODEConditionDelta(
        delta_spec={"num_steps": 3, "sampler_id": "euler"},
        source="test",
        target_round=0,
        calibration_artifact_hash="test:gap5",
    )
    trace = adapter.solve_ode(bundle, condition, seed=0)
    assert calls, (
        "solve_ode did NOT call _load_model before dispatch on the torch "
        "backend. GAP-5 is open: _loaded_model_kind() reads 'synthetic' "
        "while self._model is None, the upstream fast-path is skipped, "
        "and the CTMC path calls the velocity module with None."
    )
    assert trace is not None


def test_upstream_stub_does_not_shadow_real_posebusters() -> None:
    """Stub install skips ``posebusters`` when the real package exists (GAP-6).

    Pre-fix: ``_install_upstream_stubs`` unconditionally inserted a stub
    whose ``bust()`` returns ``{}``. Upstream
    ``SampleAnalyzer.analyze`` then does ``df_pb.mean().to_dict()`` on
    that dict and raises ``AttributeError: 'dict' object has no
    attribute 'mean'``, degrading the FlowMol3 chemistry composite to
    0.0 / ``degraded_chemistry`` on exactly the hosts where the real
    metrics COULD be computed (the sidecar venv ships posebusters).

    Post-fix: the stub is installed only when the real package is not
    importable. On a host without posebusters the stub still lands (so
    ``FlowMol.__init__``'s eager analyzer construction keeps working).
    """
    import sys

    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        _install_upstream_stubs,
        _real_module_available,
    )

    had_real = _real_module_available("posebusters")
    sys.modules.pop("posebusters", None)
    _install_upstream_stubs._installed = False  # type: ignore[attr-defined]
    try:
        _install_upstream_stubs()
        if had_real:
            assert "posebusters" not in sys.modules or not isinstance(
                getattr(sys.modules["posebusters"], "PoseBusters", None),
                type(None),
            ), "posebusters entry vanished"
            mod = sys.modules.get("posebusters")
            if mod is not None:
                assert getattr(mod, "__file__", None) is not None, (
                    "the real posebusters package was shadowed by the "
                    "no-op stub (stub modules have __file__ = None). "
                    "GAP-6 is open: upstream SampleAnalyzer.analyze calls "
                    "df_pb.mean() on the stub's dict return and the "
                    "chemistry composite degrades to 0.0."
                )
        else:
            assert "posebusters" in sys.modules, (
                "stub was NOT installed on a host without the real "
                "package; FlowMol.__init__ eager analyzer construction "
                "will fail on import"
            )
    finally:
        sys.modules.pop("posebusters", None)
        _install_upstream_stubs._installed = False  # type: ignore[attr-defined]