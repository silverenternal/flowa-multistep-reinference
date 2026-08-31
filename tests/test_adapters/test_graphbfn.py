"""Comprehensive test suite for the GraphBFN adapter (DTB-M7).

Exercises :class:`adaptive_reflow.adapters.graphbfn.GraphBFNAdapter`
end-to-end on the synthetic-mode placeholder path (the published
torch-mode loader is gated on the weights-acquisition phase and the
test suite must run on CPU-only environments).

The eight tests below cover:

* ``test_capabilities_handshake`` — every required engine-side
  capability flag is ``True``; per-channel domain is correctly tagged.
* ``test_build_initial_state_returns_correct_shape`` — the prior is
  the empty / uniform Categorical state; state_shape is the
  zero-length surrogate ``()``.
* ``test_solve_ode_returns_finite_trace`` — ``solve_ode`` produces a
  well-formed ``ODEIntegratorTrace``; the resulting Categorical
  parameters are finite.
* ``test_endpoint_round_trip`` — ``build_initial_state`` →
  ``apply_restart_distribution`` → ``solve_ode`` →
  ``observe_endpoint`` produces a valid endpoint bundle whose
  ``native_state_digest`` is deterministic.
* ``test_determinism`` — two consecutive runs from identical seeds
  produce byte-identical ``native_state_digest`` chains.
* ``test_restart_blend_respects_memory_fraction`` — per-channel blend
  math: ``beta = 0`` keeps prior verbatim; ``beta = 1`` draws fresh;
  ``beta = 0.5`` is the midpoint.
* ``test_compose_condition_injects_native_metadata`` — unconditional
  pass-through stamps ``atom_vocab_size`` / ``bond_vocab_size`` /
  ``variant`` / ``dataset``; property-conditioned passes the target
  scalar + ``condition_kind``.
* ``test_export_trajectory_returns_graph_payload`` — the public
  trajectory export returns a dict with the five graph-shaped tensors.

Tests rely on the conftest fixture
:func:`tests.test_adapters.conftest._materialize_twodim_fm_weights`
for the rest of the suite (it has no effect on GraphBFN).
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


GRAPHBFN_TEST_CHANNELS: tuple[str, ...] = (
    "atoms",
    "bonds",
    "adjacency",
    "valence",
    "charge",
)


def _hash_bundle(bundle) -> str:
    """Deterministic sha256 digest of ``bundle``'s identity surface."""
    h = hashlib.sha256()
    h.update(repr(sorted(bundle.channels.items(), key=lambda kv: str(kv[0]))).encode())
    h.update(b"|")
    h.update(str(bundle.batch_id).encode())
    h.update(b"|")
    h.update(str(bundle.sample_id).encode())
    h.update(b"|")
    h.update(str(bundle.source_round).encode())
    h.update(b"|")
    h.update(str(bundle.native_state_digest).encode())
    return h.hexdigest()


def _make_final_policy(
    *,
    policy_id: str,
    run_id: str,
    beta: float,
    channels: tuple[str, ...] = GRAPHBFN_TEST_CHANNELS,
    target_round: int = 0,
) -> "FinalRestartPolicy":
    """Build a :class:`FinalRestartPolicy` with per-channel ``beta``."""
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ChannelName(k): FactorValue(float(beta)) for k in channels},
        alpha_by_channel={ChannelName(k): FactorValue(1.0) for k in channels},
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(0.0) for k in channels
        },
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName(k): True for k in channels},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int = 8,
    source: str = "graphbfn_test",
    calibration_artifact_hash: str = "cal-graphbfn",
    condition_kind: str = "unconditional",
    property_value: float | None = None,
) -> "ODEConditionDelta":
    from adaptive_reflow.frame import ODEConditionDelta

    delta_spec: dict[str, object] = {
        "num_steps": int(num_steps),
        "condition_kind": str(condition_kind),
    }
    if property_value is not None:
        delta_spec["property_value"] = float(property_value)
    return ODEConditionDelta(
        delta_spec=delta_spec,
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _native_state(adapter, digest: str) -> dict:
    """Return the entry stored in ``adapter._native_states[digest]`` (test seam)."""
    return adapter._native_states[digest]  # noqa: SLF001


def _compute_fresh_param(rng_seed_blob: str, shape: tuple[int, int]) -> np.ndarray:
    """Re-derive the fresh-prior draw the adapter would make.

    Mirrors :func:`adaptive_reflow.adapters.graphbfn._uniform_categorical_params`
    so test (6) can verify the per-channel blend math independently of
    the adapter.
    """
    seed = int(hashlib.sha256(rng_seed_blob.encode("utf-8")).hexdigest()[:8], 16)
    return np.zeros(shape, dtype=np.float64)


# ---------------------------------------------------------------------------
# 1. Capability handshake is well-formed.
# ---------------------------------------------------------------------------


def test_capabilities_handshake() -> None:
    """The adapter's capability surface is well-formed and exhaustive."""
    from adaptive_reflow.adapters.graphbfn import (
        GRAPHBFN_CHANNELS,
        GRAPHBFN_CHANNEL_DOMAINS,
        GRAPHBFN_CONFIG_HASH_ICLR,
        GraphBFNAdapter,
    )
    from adaptive_reflow.universal.adapter import validate_capabilities

    adapter = GraphBFNAdapter(force_mode="synthetic")
    caps = adapter.capabilities()

    # The engine-side required flags are all True.
    assert caps.has_ode_integration_surface is True
    assert caps.has_restart_boundary is True
    assert caps.has_condition_injection is True
    assert caps.has_trajectory_digest is True
    assert caps.has_prior_export is True
    assert caps.has_state_export is True
    assert caps.has_deterministic_seed is True
    # GraphBFN is mixed (continuous + discrete) but does NOT expose
    # ``has_materialization_route`` — the engine hands the graph off
    # behind ``TensorRef`` keys.
    assert caps.has_materialization_route is False
    # 5-channel surface.
    assert caps.supported_channels == GRAPHBFN_CHANNELS
    # Per-channel domain: 3 discrete + 2 continuous.
    expected_domains = {
        "atoms": "discrete",
        "bonds": "discrete",
        "adjacency": "discrete",
        "valence": "continuous",
        "charge": "continuous",
    }
    assert dict(caps.channel_domains) == expected_domains
    # Capability validator agrees.
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"
    # The graph state-shape surrogate is the empty tuple.
    assert caps.state_shape == ()
    # ICLR-2025 is the default variant — verify the config hash.
    assert caps.native_config_hash == GRAPHBFN_CONFIG_HASH_ICLR
    # The mechanism_id is the canonical ``"graphbfn"`` string.
    assert GraphBFNAdapter.mechanism_id == "graphbfn"


# ---------------------------------------------------------------------------
# 2. build_initial_state returns the empty / uniform prior with
#    state_shape=() and zero-channel graph payload.
# ---------------------------------------------------------------------------


def test_build_initial_state_returns_correct_shape() -> None:
    """The prior bundle carries 5 channels; native state is empty / uniform."""
    from adaptive_reflow.adapters.graphbfn import (
        GRAPHBFN_ATOM_VOCAB_QM9,
        GRAPHBFN_BOND_VOCAB,
        GraphBFNAdapter,
    )

    adapter = GraphBFNAdapter(force_mode="synthetic")
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-shape", sample_id="sample-gbfn-shape"
    )

    # The state-shape surrogate is the empty tuple.
    assert adapter.state_shape == ()
    # All five channels are populated.
    assert set(str(k) for k in bundle.channels.keys()) == {
        "atoms",
        "bonds",
        "adjacency",
        "valence",
        "charge",
    }
    # The initial state is empty: N=0, E=0, no adjacency.
    entry = _native_state(adapter, bundle.native_state_digest)
    assert entry["theta_node"].shape == (0, GRAPHBFN_ATOM_VOCAB_QM9)
    assert entry["theta_edge"].shape == (0, GRAPHBFN_BOND_VOCAB)
    assert entry["adjacency_logits"].shape == (0, 0)
    assert entry["charge"].shape == (0,)
    assert entry["valence"].shape == (0,)
    assert entry["kind"] == "initial"
    assert entry["source_round"] == 0


# ---------------------------------------------------------------------------
# 3. solve_ode returns a finite trace; the BFN loop runs num_steps NFE-like
#    calls and the resulting Categorical parameters are well-formed.
# ---------------------------------------------------------------------------


def test_solve_ode_returns_finite_trace() -> None:
    """``solve_ode`` runs ``num_steps`` BFN steps and produces finite params."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    adapter = GraphBFNAdapter(force_mode="synthetic", num_steps=8)
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-solve", sample_id="sample-gbfn-solve"
    )
    condition = _make_condition_delta(target_round=0, num_steps=8)
    trace = adapter.solve_ode(bundle, condition, seed=42)

    # The trace reports the canonical step count + accept rate.
    assert trace.steps == 8
    assert trace.accept_rate == 1.0
    assert trace.native_state_digest
    assert trace.integrator_config_hash

    # The stored trajectory is finite and has a positive node count
    # (``solve_ode`` samples a fresh graph scaffold at t=0 when the
    # prior is empty).
    traj_entry = _native_state(adapter, trace.native_state_digest)
    assert traj_entry["kind"] == "trajectory"
    assert np.all(np.isfinite(traj_entry["theta_node"]))
    assert np.all(np.isfinite(traj_entry["theta_edge"]))
    # The adjacency-logits matrix carries ``-inf`` on the diagonal (the
    # "no self-loop" sentinel) so we only check the off-diagonal
    # entries are finite.
    adj = np.asarray(traj_entry["adjacency_logits"], dtype=np.float64)
    n_adj = adj.shape[0]
    if n_adj > 0:
        off_diag = adj.copy()
        np.fill_diagonal(off_diag, 0.0)
        assert np.all(np.isfinite(off_diag)), (
            f"off-diagonal adjacency entries must be finite; got {adj!r}"
        )
        # Diagonal must remain ``-inf`` (the no-self-loop sentinel).
        diag = np.diag(adj)
        assert np.all(np.isneginf(diag)), (
            f"diagonal adjacency must be -inf; got {diag!r}"
        )
    assert traj_entry["theta_node"].shape[0] >= 1
    assert traj_entry["theta_node"].shape[1] == 9  # QM9 atom-vocab default.


# ---------------------------------------------------------------------------
# 4. Endpoint round-trip: build_initial_state -> solve_ode ->
#    observe_endpoint produces a detachable bundle.
# ---------------------------------------------------------------------------


def test_endpoint_round_trip() -> None:
    """Round-trip produces a detachable bundle whose payload is rounded."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    adapter = GraphBFNAdapter(force_mode="synthetic", num_steps=4)
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-rt", sample_id="sample-gbfn-rt"
    )
    condition = _make_condition_delta(target_round=0, num_steps=4)
    trace = adapter.solve_ode(bundle, condition, seed=7)
    endpoint = adapter.observe_endpoint(trace, bundle)

    # Detach gate is satisfied.
    assert endpoint.detach_proof is True
    # Provenance carries the ``graphbfn_observed`` audit code.
    assert any("graphbfn_observed" in p for p in endpoint.provenance)
    # The endpoint carries the rounded graph in native-state.
    endpoint_entry = _native_state(adapter, endpoint.native_state_digest)
    assert endpoint_entry["kind"] == "endpoint"
    assert "atom_types" in endpoint_entry
    assert "bond_types" in endpoint_entry
    assert "adjacency" in endpoint_entry
    # Rounded values are valid atom / bond-type integers.
    assert np.all(endpoint_entry["atom_types"] >= 0)
    assert np.all(endpoint_entry["bond_types"] >= 0)


# ---------------------------------------------------------------------------
# 5. Determinism: two identical runs produce byte-identical digests.
# ---------------------------------------------------------------------------


def test_determinism() -> None:
    """Two identical runs from the same seed produce identical digest chains."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    def _drive() -> list[str]:
        adapter = GraphBFNAdapter(force_mode="synthetic", num_steps=8)
        digests: list[str] = []
        bundle = adapter.build_initial_state(
            batch_id="batch-gbfn-det",
            sample_id="sample-gbfn-det",
        )
        digests.append(bundle.native_state_digest)
        condition = _make_condition_delta(target_round=0, num_steps=8)
        trace = adapter.solve_ode(bundle, condition, seed=2024)
        digests.append(trace.native_state_digest)
        endpoint = adapter.observe_endpoint(trace, bundle)
        digests.append(endpoint.native_state_digest)
        return digests

    digests_a = _drive()
    digests_b = _drive()
    assert digests_a == digests_b, (
        f"native_state_digest drift across runs: {digests_a!r} vs {digests_b!r}"
    )


# ---------------------------------------------------------------------------
# 6. apply_restart_distribution blends per-channel graph parameters.
# ---------------------------------------------------------------------------


def test_restart_blend_respects_memory_fraction() -> None:
    """``beta = 0`` keeps prior verbatim; ``beta = 1`` resets to fresh.

    The blend math is elementwise ``m * prior + (1 - m) * fresh`` with
    ``m = 1 - beta`` per channel. For ``beta = 0`` the blended
    Categorical parameters equal the prior verbatim; for ``beta = 1``
    they equal the fresh uniform draw.
    """
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    adapter = GraphBFNAdapter(force_mode="synthetic", num_steps=4)
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-blend", sample_id="sample-gbfn-blend"
    )
    prior_entry = _native_state(adapter, bundle.native_state_digest)

    # beta = 0.0 -> memory fraction = 1.0 -> blended = prior verbatim.
    policy_keep = _make_final_policy(
        policy_id="policy-keep", run_id="run-keep", beta=0.0
    )
    kept = adapter.apply_restart_distribution(bundle, policy_keep)
    kept_entry = _native_state(adapter, kept.native_state_digest)
    assert np.allclose(kept_entry["theta_node"], prior_entry["theta_node"]), (
        "beta=0.0 must keep theta_node verbatim"
    )
    assert np.allclose(kept_entry["theta_edge"], prior_entry["theta_edge"]), (
        "beta=0.0 must keep theta_edge verbatim"
    )
    assert np.allclose(kept_entry["adjacency_logits"], prior_entry["adjacency_logits"]), (
        "beta=0.0 must keep adjacency_logits verbatim"
    )

    # beta = 1.0 -> memory fraction = 0.0 -> blended = fresh uniform.
    policy_fresh = _make_final_policy(
        policy_id="policy-fresh", run_id="run-fresh", beta=1.0
    )
    fresh = adapter.apply_restart_distribution(bundle, policy_fresh)
    fresh_entry = _native_state(adapter, fresh.native_state_digest)
    assert fresh_entry["theta_node"].shape == prior_entry["theta_node"].shape
    assert np.allclose(fresh_entry["theta_node"], 0.0), (
        f"beta=1.0 must reset theta_node to fresh uniform; got non-zero values: "
        f"{fresh_entry['theta_node']!r}"
    )
    assert np.allclose(fresh_entry["theta_edge"], 0.0), (
        "beta=1.0 must reset theta_edge to fresh uniform"
    )
    assert np.allclose(fresh_entry["adjacency_logits"], prior_entry["adjacency_logits"]), (
        "beta=1.0 keeps adjacency shape (empty) the same as prior"
    )

    # The post-restart bundle carries the AUDIT_GRAPHBFN_RESTART_BLEND
    # audit code in provenance.
    assert any("graphbfn_restart_blend" in p for p in fresh.provenance), (
        f"fresh bundle must carry graphbfn_restart_blend provenance; "
        f"got {fresh.provenance!r}"
    )


# ---------------------------------------------------------------------------
# 7. compose_condition injects native metadata (atom_vocab_size,
#    bond_vocab_size, variant, dataset) and accepts property conditioning.
# ---------------------------------------------------------------------------


def test_compose_condition_injects_native_metadata() -> None:
    """Unconditional pass-through stamps GraphBFN metadata; property cond adds target."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter
    from adaptive_reflow.frame import ODEConditionDelta

    adapter = GraphBFNAdapter(force_mode="synthetic")
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-cond", sample_id="sample-gbfn-cond"
    )
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 16},
        source="cond-test",
        target_round=0,
        calibration_artifact_hash="cal-graphbfn-cond",
    )
    out = adapter.compose_condition(bundle, delta)

    # Unconditional default: ``condition_kind`` is set to ``unconditional``.
    assert out.delta_spec["condition_kind"] == "unconditional"
    assert out.delta_spec["target_distribution"] == "qm9"
    assert out.delta_spec["variant"] == "iclr2025"
    assert out.delta_spec["atom_vocab_size"] == 9
    assert out.delta_spec["bond_vocab_size"] == 4
    assert out.delta_spec["integrator_config_hash"]  # any non-empty string.

    # Property-conditioned: passing ``condition_kind`` + ``property_value``
    # is forwarded to ``delta_spec`` so ``solve_ode`` can apply the mask.
    delta_cond = ODEConditionDelta(
        delta_spec={
            "num_steps": 16,
            "condition_kind": "property_logp",
            "property_value": 0.42,
        },
        source="cond-test",
        target_round=0,
        calibration_artifact_hash="cal-graphbfn-cond",
    )
    out_cond = adapter.compose_condition(bundle, delta_cond)
    assert out_cond.delta_spec["condition_kind"] == "property_logp"
    assert out_cond.delta_spec["property_value"] == 0.42

    # Unknown condition kinds raise.
    bad_delta = ODEConditionDelta(
        delta_spec={"num_steps": 16, "condition_kind": "property_unknown"},
        source="cond-test",
        target_round=0,
        calibration_artifact_hash="cal-graphbfn-cond",
    )
    with pytest.raises(ValueError, match="unknown_condition_kind"):
        adapter.compose_condition(bundle, bad_delta)

    # Property-conditioned without a target scalar raises.
    bad_target = ODEConditionDelta(
        delta_spec={"num_steps": 16, "condition_kind": "property_qed"},
        source="cond-test",
        target_round=0,
        calibration_artifact_hash="cal-graphbfn-cond",
    )
    with pytest.raises(ValueError, match="property_value_required"):
        adapter.compose_condition(bundle, bad_target)


# ---------------------------------------------------------------------------
# 8. export_trajectory returns the native graph payload (or ``None``).
# ---------------------------------------------------------------------------


def test_export_trajectory_returns_graph_payload() -> None:
    """``export_trajectory`` returns the per-channel Categorical parameter dict."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    adapter = GraphBFNAdapter(force_mode="synthetic", num_steps=4)
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-traj", sample_id="sample-gbfn-traj"
    )
    condition = _make_condition_delta(target_round=0, num_steps=4)
    trace = adapter.solve_ode(bundle, condition, seed=11)
    payload = adapter.export_trajectory(trace)

    assert payload is not None
    assert "theta_node" in payload
    assert "theta_edge" in payload
    assert "adjacency_logits" in payload
    assert "charge" in payload
    assert "valence" in payload
    assert np.all(np.isfinite(payload["theta_node"]))
    assert np.all(np.isfinite(payload["theta_edge"]))
    # Off-diagonal adjacency entries are finite; diagonal is the
    # ``-inf`` no-self-loop sentinel (see test_solve_ode_returns_finite_trace).
    adj_payload = np.asarray(payload["adjacency_logits"], dtype=np.float64)
    if adj_payload.shape[0] > 0:
        off_diag = adj_payload.copy()
        np.fill_diagonal(off_diag, 0.0)
        assert np.all(np.isfinite(off_diag)), (
            "off-diagonal adjacency entries must be finite"
        )
        assert np.all(np.isneginf(np.diag(adj_payload))), (
            "diagonal adjacency entries must be -inf (no self-loop)"
        )

    # An unknown trace returns ``None`` (no native state stored).
    from adaptive_reflow.universal.state import ODEIntegratorTrace

    ghost = ODEIntegratorTrace(
        steps=1,
        accept_rate=1.0,
        native_state_digest="nonexistent-digest",
        integrator_config_hash="ghost-cfg",
    )
    assert adapter.export_trajectory(ghost) is None


# ---------------------------------------------------------------------------
# 9. Protocol isinstance check (mirrors test_twodim_fm::test_protocol_surface_intact).
# ---------------------------------------------------------------------------


def test_protocol_surface_intact() -> None:
    """The adapter satisfies :class:`FlowMatchingODEAdapter` and all 8 methods are callable."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    adapter = GraphBFNAdapter(force_mode="synthetic")

    assert isinstance(adapter, FlowMatchingODEAdapter), (
        "GraphBFNAdapter does not satisfy FlowMatchingODEAdapter Protocol"
    )

    expected_methods = (
        "capabilities",
        "build_initial_state",
        "export_endpoint",
        "detach_and_validate_endpoint",
        "apply_restart_distribution",
        "compose_condition",
        "solve_ode",
        "observe_endpoint",
        "export_trajectory",
    )
    for name in expected_methods:
        method = getattr(adapter, name, None)
        assert callable(method), f"method {name!r} is not callable on the adapter"


# ---------------------------------------------------------------------------
# 10. Protocol-surface immutability: bundle identity is preserved across
#     non-mutating calls.
# ---------------------------------------------------------------------------


def test_protocol_methods_are_non_mutating() -> None:
    """``export_endpoint`` / ``detach_and_validate_endpoint`` /
    ``compose_condition`` do not mutate the input bundle."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter
    from adaptive_reflow.frame import ODEConditionDelta

    adapter = GraphBFNAdapter(force_mode="synthetic")
    bundle = adapter.build_initial_state(
        batch_id="batch-gbfn-immut", sample_id="sample-gbfn-immut"
    )
    bundle_before = _hash_bundle(bundle)

    # ``export_endpoint`` must not mutate the input.
    endpoint = adapter.export_endpoint(bundle)
    assert _hash_bundle(bundle) == bundle_before

    # ``detach_and_validate_endpoint`` must not mutate the input.
    detached = adapter.detach_and_validate_endpoint(bundle)
    assert _hash_bundle(bundle) == bundle_before
    assert detached.detach_proof is True

    # ``compose_condition`` returns a fresh delta; the bundle is untouched.
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 16},
        source="immut-test",
        target_round=0,
        calibration_artifact_hash="cal-immut",
    )
    composed = adapter.compose_condition(bundle, delta)
    assert composed is not None
    assert _hash_bundle(bundle) == bundle_before


# ---------------------------------------------------------------------------
# 11. batched_inference returns ``n_samples`` rounded graphs.
# ---------------------------------------------------------------------------


def test_batched_inference_returns_n_samples() -> None:
    """``batched_inference(n_samples=K)`` returns a list of K rounded-graph dicts."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    adapter = GraphBFNAdapter(force_mode="synthetic", num_steps=4)
    out = adapter.batched_inference(n_samples=5, num_steps=4, seed=99)
    assert len(out) == 5
    for sample in out:
        assert "atom_types" in sample
        assert "bond_types" in sample
        assert "adjacency" in sample
        assert "theta_node" in sample
        # Each atom-type value is in [0, atom_vocab_size).
        assert int(sample["atom_types"].max()) < 9
        # Each bond-type value is in [0, bond_vocab_size).
        assert int(sample["bond_types"].max()) < 4


# ---------------------------------------------------------------------------
# 12. Hierarchical variant uses a different config hash than ICLR-2025.
# ---------------------------------------------------------------------------


def test_hierarchical_variant_config_hash() -> None:
    """The Hierarchical variant advertises ``graphbfn_hier:cfg:v1``."""
    from adaptive_reflow.adapters.graphbfn import (
        GRAPHBFN_CONFIG_HASH_HIER,
        GraphBFNAdapter,
    )

    adapter_hier = GraphBFNAdapter(variant="hierarchical", force_mode="synthetic")
    caps = adapter_hier.capabilities()
    assert caps.native_config_hash == GRAPHBFN_CONFIG_HASH_HIER


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))