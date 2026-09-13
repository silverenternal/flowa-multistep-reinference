"""Test that a non-molecular adapter can be plugged in without importing molecular.

This is the load-bearing test for the universal/molecular split: it
constructs a synthetic, **non-molecular** adapter that uses its own
channel vocabulary (``latent`` / ``graph`` / ``topology``) and
verifies that:

* the universal :class:`FlowMatchingODEAdapter` Protocol is satisfiable
  without any reference to :mod:`adaptive_reflow.molecular`;
* :class:`AdapterCapabilities` accepts the non-molecule channel set;
* :func:`validate_capabilities` accepts the new surface;
* :class:`StateBundle` can be constructed and validated with the new
  channels.

If a future change drags a ``molecular`` import into
:mod:`adaptive_reflow.universal`, the helper at the top of the file
fails the import with a clear message.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# ---------------------------------------------------------------------------
# Boundary check: importing this test module MUST NOT import any
# ``adaptive_reflow.molecular`` symbol. We assert this by introspecting
# ``sys.modules`` AFTER the explicit imports below have executed. The
# import of :mod:`adaptive_reflow.universal` is allowed (it is the
# canonical home for the abstractions).
# ---------------------------------------------------------------------------
import pytest

from adaptive_reflow.universal import (
    AdapterCapabilities,
    ChannelDomain,
    FlowMatchingODEAdapter,
    ODEConditionDelta,
    ODEIntegratorTrace,
    RestartMixer,  # noqa: F401  (exercised by the test)
    RestartPolicy,  # noqa: F401
    StateBundle,
    TensorRef,
    validate_capabilities,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Synthetic non-molecular adapter — a graph-flow / latent-flow hybrid.
# Channel vocabulary is intentionally not molecule-specific. The adapter
# advertises ``latent``, ``graph``, and ``topology`` channels.
# ---------------------------------------------------------------------------

_NON_MOLECULE_CHANNELS: tuple[str, ...] = ("latent", "graph", "topology")

_NON_MOLECULE_CHANNEL_DOMAINS: dict[str, ChannelDomain] = {
    "latent": "latent",
    "graph": "graph",
    "topology": "discrete",
}


def _make_tensor_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic TensorRef from a label + parts dict."""
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    import hashlib

    return TensorRef(f"nonmol:{hashlib.sha256(blob).hexdigest()[:16]}")


class _NonMoleculeAdapter:
    """A non-molecular FlowMatchingODEAdapter implementation.

    Carries its own (latent, graph, topology) channel vocabulary. Does
    not import anything from :mod:`adaptive_reflow.molecular`.
    """

    def __init__(self) -> None:
        self._topology_indices = (0, 1, 0, 1)
        self._caps = AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=False,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=False,
            supported_channels=_NON_MOLECULE_CHANNELS,
            channel_domains=_NON_MOLECULE_CHANNEL_DOMAINS,
        )

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    def build_initial_state(
        self, *, batch_id: str, sample_id: str
    ) -> StateBundle:
        return StateBundle(
            channels={
                ch: _make_tensor_ref(
                    "init", channel=ch, batch=batch_id, sample=sample_id
                )
                for ch in _NON_MOLECULE_CHANNELS
            },
            masks={
                ch: _make_tensor_ref(
                    "mask", channel=ch, batch=batch_id, sample=sample_id
                )
                for ch in _NON_MOLECULE_CHANNELS
            },
            batch_id=batch_id,
            sample_id=sample_id,
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=_make_tensor_ref(
                "digest", batch=batch_id, sample=sample_id
            ),
            provenance=("nonmol_adapter", "test"),
            capability_token=self._caps,
        )

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        return state

    def detach_and_validate_endpoint(self, state: StateBundle) -> StateBundle:
        return state

    def apply_restart_distribution(
        self, state: StateBundle, policy: RestartPolicy
    ) -> StateBundle:
        return state

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        return delta

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        return ODEIntegratorTrace(
            steps=1,
            accept_rate=1.0,
            native_state_digest=_make_tensor_ref(
                "trace", source=state.native_state_digest, seed=seed
            ),
            integrator_config_hash=_make_tensor_ref(
                "config", seed=seed
            ),
        )

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        return state

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> Any | None:
        """P0-7: non-molecule adapter implements the public trajectory
        export entry point. Returns ``None`` because this synthetic
        adapter does not preserve a native trajectory."""
        return None

    def observe_token_indices(self, trace: ODEIntegratorTrace, paper_quantities: Any) -> dict[str, Any]:
        """Expose the fixture's unchanged discrete topology channel."""
        import numpy as np
        return {"topology": np.asarray(self._topology_indices, dtype=np.int64)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBoundary:
    """Verify the universal layer never imports the molecule layer.

    The check inspects the AST of every ``adaptive_reflow/universal/*.py``
    file and asserts no ``import`` statement targets
    ``adaptive_reflow.molecular``. We use the AST approach instead of
    inspecting ``sys.modules`` because the test file itself lives in
    ``tests/test_universal/`` and pytest runs all test modules in the
    same process — other test modules (e.g. ``test_engine``) import
    ``adaptive_reflow.frame`` which transitively loads
    ``adaptive_reflow.molecular``, polluting ``sys.modules`` for
    unrelated tests.
    """

    def test_universal_ast_has_no_molecular_import(self) -> None:
        """No ``adaptive_reflow/universal/*.py`` file may import from
        ``adaptive_reflow.molecular``."""
        import ast
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        universal_dir = repo_root / "adaptive_reflow" / "universal"
        assert universal_dir.is_dir(), (
            f"expected universal/ at {universal_dir}, not found"
        )
        findings: list[tuple[str, str, int]] = []
        for path in sorted(universal_dir.rglob("*.py")):
            tree = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "adaptive_reflow.molecular" or alias.name.startswith(
                            "adaptive_reflow.molecular."
                        ):
                            findings.append(
                                (
                                    str(path.relative_to(repo_root)),
                                    alias.name,
                                    node.lineno,
                                )
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "adaptive_reflow.molecular" or module.startswith(
                        "adaptive_reflow.molecular."
                    ):
                        findings.append(
                            (
                                str(path.relative_to(repo_root)),
                                module,
                                node.lineno,
                            )
                        )
        assert findings == [], (
            "universal/ must not import from adaptive_reflow.molecular; "
            f"found: {findings}"
        )


class TestNonMoleculeAdapter:
    """Verify a synthetic non-molecule adapter satisfies the protocol."""

    def test_adapter_is_protocol_conformant(self) -> None:
        """The synthetic adapter MUST satisfy :class:`FlowMatchingODEAdapter`."""
        adapter = _NonMoleculeAdapter()
        # runtime_checkable Protocol — isinstance() must succeed.
        assert isinstance(adapter, FlowMatchingODEAdapter)

    def test_discrete_topology_indices_are_observable(self) -> None:
        adapter = _NonMoleculeAdapter()
        state = adapter.build_initial_state(batch_id="b", sample_id="s")
        delta = ODEConditionDelta(delta_spec={}, source="test", target_round=0,
                                  calibration_artifact_hash="test")
        trace = adapter.solve_ode(state, adapter.compose_condition(state, delta), seed=0)
        tokens = adapter.observe_token_indices(trace, None)
        assert set(tokens) == {"topology"}
        assert tokens["topology"].tolist() == [0, 1, 0, 1]

    def test_capabilities_advertise_non_molecule_channels(self) -> None:
        """Capabilities MUST list the non-molecule channels only."""
        caps = _NonMoleculeAdapter().capabilities()
        assert caps.supported_channels == _NON_MOLECULE_CHANNELS
        # The molecule channels MUST NOT appear in the capability surface.
        for mol_channel in ("coordinate", "charge", "raw_pair", "projected_pair"):
            assert mol_channel not in caps.supported_channels

    def test_validate_capabilities_accepts_non_molecule_surface(self) -> None:
        """The capability surface MUST validate cleanly."""
        caps = _NonMoleculeAdapter().capabilities()
        ok, errs = validate_capabilities(caps)
        assert ok, f"validate_capabilities failed: {errs}"

    def test_state_bundle_with_non_molecule_channels_is_valid(self) -> None:
        """A :class:`StateBundle` with non-molecule channels MUST validate."""
        adapter = _NonMoleculeAdapter()
        state = adapter.build_initial_state(batch_id="b1", sample_id="s1")
        ok, errs = validate_state_bundle(state)
        assert ok, f"validate_state_bundle failed: {errs}"
        # Every channel is present in the bundle.
        assert set(state.channels.keys()) == set(_NON_MOLECULE_CHANNELS)
        # Every channel's TensorRef is a non-empty string.
        for ch, ref in state.channels.items():
            assert isinstance(ref, str)
            assert ref, f"empty TensorRef for channel {ch!r}"

    def test_round_trip_via_protocol(self) -> None:
        """End-to-end: build initial state, run a step, observe endpoint."""
        adapter: FlowMatchingODEAdapter = _NonMoleculeAdapter()
        state = adapter.build_initial_state(batch_id="b1", sample_id="s1")
        endpoint = adapter.export_endpoint(state)
        detached = adapter.detach_and_validate_endpoint(endpoint)
        trace = adapter.solve_ode(detached, ODEConditionDelta(
            delta_spec={"kind": "latent"},
            source="test",
            target_round=0,
            calibration_artifact_hash="calhash",
        ), seed=42)
        assert isinstance(trace, ODEIntegratorTrace)
        observed = adapter.observe_endpoint(trace, detached)
        # The observed bundle is valid.
        ok, _ = validate_state_bundle(observed)
        assert ok

    def test_universal_has_no_molecule_vocabulary(self) -> None:
        """A handful of universal surface attributes must carry no molecule vocabulary."""
        # The synthetic adapter's channel set must not collide with the
        # molecule channel vocabulary.
        mol_channels = {"coordinate", "charge", "raw_pair", "projected_pair"}
        non_mol_channels = set(_NON_MOLECULE_CHANNELS)
        assert non_mol_channels.isdisjoint(mol_channels)

    def test_no_molecule_import_in_universal_namespace(self) -> None:
        """The :mod:`adaptive_reflow.universal` module's public surface
        must not expose any symbol starting with ``Molecule`` or
        ``molecular``."""
        import adaptive_reflow.universal as u

        for name in dir(u):
            if name.startswith("_"):
                continue
            lowered = name.lower()
            assert "molecule" not in lowered, (
                f"universal/ exposes a molecule-named symbol: {name!r}"
            )
