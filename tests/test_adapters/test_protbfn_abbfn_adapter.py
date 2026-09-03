"""Tests for the ProtBFN / AbBFN / AbBFN2 adapter (R16).

The :class:`adaptive_reflow.adapters.protbfn_abbfn_adapter
.ProtBFNAbBFNAdapter` wraps the published InstaDeep Bayesian Flow Network
(BFN) generative models for protein sequences into the framework's
:class:`FlowMatchingODEAdapter` Protocol. Tests exercise the 8-method
Protocol surface, the capability handshake, the LRU-bounded native-
state cache, and the byte-deterministic refinement loop in *synthetic*
mode (the production path requires ``[protein-bfn]`` extra + the
published ProtBFN / AbBFN / AbBFN2 weights).

Tests:

* ``test_capabilities_handshake`` - capability surface is well-formed.
* ``test_build_initial_state_returns_correct_shape`` - ``(L, 22)``
  per-position uniform categorical prior.
* ``test_solve_ode_returns_finite_trace`` - ``num_steps`` discrete BFN
  refinements produce a finite ``(N+1, L, 22)`` trajectory.
* ``test_endpoint_round_trip`` - ``observe_endpoint`` returns a bundle
  whose digest resolves to ``(L, 22)``.
* ``test_determinism`` - two calls with the same seed produce byte-
  identical endpoint digests.
* ``test_velocity_field_lazy_loads_torch_if_required`` - the adapter
  only imports torch when ``force_mode='torch'`` is explicitly
  requested.
* ``test_mechanism_id_per_checkpoint`` - ``mechanism_id`` returns
  ``"ProtBFN"`` / ``"AbBFN"`` / ``"AbBFN2"`` per the loaded checkpoint.
* ``test_compose_condition_validates_inpainting`` - inpainting fields
  are validated; bad inputs raise ``ValueError``.
* ``test_restart_blend_respects_memory_fraction`` -
  ``apply_restart_distribution`` for ``beta in {0.0, 0.5, 1.0}``.
* ``test_inject_forward_noise_hook`` - the per-position categorical is
  perturbed and the ``forward_noise_applied`` provenance tag is
  appended.
* ``test_adapter_satisfies_protocol`` - the adapter passes the
  ``@runtime_checkable`` Protocol check via ``isinstance``.
"""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_bundle(bundle) -> str:
    """Return a deterministic SHA-256 digest of ``bundle``'s identity surface."""
    import hashlib as _hl

    h = _hl.sha256()
    h.update(
        repr(
            sorted(bundle.channels.items(), key=lambda kv: str(kv[0]))
        ).encode()
    )
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
    target_round: int = 0,
    beta_from_schedule: bool = False,
) -> object:
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

    channel = ChannelName("amino_acid_categorical")
    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=bool(beta_from_schedule),
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_phase_state(*, horizon_remaining: int = 200) -> object:
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="protbfn-test-lineage",
        recorded_at_round=0,
    )


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int | None = None,
    source: str = "protbfn_test",
    calibration_artifact_hash: str = "cal-protbfn",
    extra: dict | None = None,
) -> object:
    from adaptive_reflow.universal.state import ODEConditionDelta

    spec: dict = {}
    if num_steps is not None:
        spec["num_steps"] = int(num_steps)
    if extra is not None:
        spec.update(extra)
    return ODEConditionDelta(
        delta_spec=spec,
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _native_theta(
    adapter, digest: str
) -> np.ndarray:
    """Return the ``theta`` stored under ``digest`` as ``(L, K)``."""
    native = adapter._native_states[digest]  # noqa: SLF001 - test seam
    return np.asarray(native["theta"], dtype=np.float64)


def _trajectory_from_trace(adapter, trace) -> np.ndarray:
    """Return the ``(N+1, L, K)`` trajectory stored under the trace digest."""
    native = adapter._native_states[trace.native_state_digest]  # noqa: SLF001
    return np.asarray(native["trajectory"], dtype=np.float64)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def protbfn_adapter() -> object:
    """Return a fresh :class:`ProtBFNAbBFNAdapter` in synthetic mode."""
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ProtBFNAbBFNAdapter,
    )

    return ProtBFNAbBFNAdapter(
        checkpoint_path=None,
        mechanism="ProtBFN",
        force_mode="synthetic",
        num_steps=4,
        max_seq_length=8,
        vocab_size=22,
        synthetic_seed=42,
    )


@pytest.fixture
def abbfn_adapter() -> object:
    """Return a fresh AbBFN adapter in synthetic mode (small L)."""
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ProtBFNAbBFNAdapter,
    )

    return ProtBFNAbBFNAdapter(
        checkpoint_path=None,
        mechanism="AbBFN",
        force_mode="synthetic",
        num_steps=4,
        max_seq_length=8,
        vocab_size=22,
        synthetic_seed=7,
    )


# ---------------------------------------------------------------------------
# 1. Capability handshake
# ---------------------------------------------------------------------------


def test_capabilities_handshake(protbfn_adapter: object) -> None:
    """The capability surface is well-formed and declares the canonical channels."""
    from adaptive_reflow.universal.adapter import validate_capabilities

    caps = protbfn_adapter.capabilities()
    assert caps.has_ode_integration_surface is True
    assert caps.has_prior_export is True
    assert caps.has_state_export is True
    assert caps.has_condition_injection is True
    assert caps.has_restart_boundary is True
    assert caps.has_discrete_channels is True
    assert caps.has_continuous_channels is True
    assert caps.has_trajectory_digest is True
    assert caps.has_deterministic_seed is True
    assert caps.has_materialization_route is True
    # Channel vocabulary: amino acid + 4 categoricals + 1 continuous.
    assert "amino_acid_categorical" in caps.supported_channels
    assert "cdr_length_categorical" in caps.supported_channels
    assert "germline_label_categorical" in caps.supported_channels
    assert "species_label_categorical" in caps.supported_channels
    assert "light_chain_locus_categorical" in caps.supported_channels
    assert "tap_continuous" in caps.supported_channels
    # Discrete channel is declared discrete; TAP continuous is declared continuous.
    assert caps.channel_domains["amino_acid_categorical"] == "discrete"
    assert caps.channel_domains["tap_continuous"] == "continuous"
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"
    # Stable config hash for the adapter family.
    assert caps.native_config_hash == "protbfn_abbfn:cfg:v1"


# ---------------------------------------------------------------------------
# 2. build_initial_state returns (L, K) per-position categorical
# ---------------------------------------------------------------------------


def test_build_initial_state_returns_correct_shape(
    protbfn_adapter: object,
) -> None:
    """``build_initial_state`` returns a (L, 22) per-position uniform categorical."""
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-1", sample_id="sample-protbfn-1"
    )
    theta = _native_theta(protbfn_adapter, bundle.native_state_digest)
    L, K = theta.shape
    assert L == int(protbfn_adapter._max_seq_length)  # noqa: SLF001
    assert K == int(protbfn_adapter._vocab_size)  # noqa: SLF001
    # Per-position categorical: rows sum to 1 (probability distribution).
    np.testing.assert_allclose(
        theta.sum(axis=1), np.ones(L), atol=1e-12
    )
    # All entries are non-negative (probabilities).
    assert np.all(theta >= 0.0)
    # Bundle carries the canonical channel.
    from adaptive_reflow.universal.state import ChannelName

    assert ChannelName("amino_acid_categorical") in bundle.channels


# ---------------------------------------------------------------------------
# 3. solve_ode returns a finite (N+1, L, K) trajectory
# ---------------------------------------------------------------------------


def test_solve_ode_returns_finite_trace(protbfn_adapter: object) -> None:
    """``num_steps`` discrete BFN refinements yield a finite trajectory."""
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-2", sample_id="sample-protbfn-2"
    )
    delta = _make_condition_delta(target_round=0, num_steps=4)
    trace = protbfn_adapter.solve_ode(bundle, delta, seed=0)
    traj = _trajectory_from_trace(protbfn_adapter, trace)
    assert traj.shape[0] == 5  # num_steps + 1
    assert traj.shape[1] == int(protbfn_adapter._max_seq_length)  # noqa: SLF001
    assert traj.shape[2] == int(protbfn_adapter._vocab_size)  # noqa: SLF001
    assert np.all(np.isfinite(traj))
    # Each row is a valid probability distribution (row-renormalized).
    for i in range(traj.shape[0]):
        np.testing.assert_allclose(
            traj[i].sum(axis=1), np.ones(traj.shape[1]), atol=1e-12
        )
        assert np.all(traj[i] >= 0.0)
    assert trace.steps == 4
    assert trace.accept_rate == 1.0


# ---------------------------------------------------------------------------
# 4. Endpoint round trip
# ---------------------------------------------------------------------------


def test_endpoint_round_trip(protbfn_adapter: object) -> None:
    """``observe_endpoint`` returns a bundle whose digest resolves to (L, K)."""
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-3", sample_id="sample-protbfn-3"
    )
    delta = _make_condition_delta(target_round=0, num_steps=4)
    trace = protbfn_adapter.solve_ode(bundle, delta, seed=0)
    endpoint_bundle = protbfn_adapter.observe_endpoint(trace, bundle)
    theta = _native_theta(protbfn_adapter, endpoint_bundle.native_state_digest)
    L, K = theta.shape
    assert L == int(protbfn_adapter._max_seq_length)  # noqa: SLF001
    assert K == int(protbfn_adapter._vocab_size)  # noqa: SLF001
    # The endpoint bundle increments source_round.
    assert endpoint_bundle.source_round == bundle.source_round + 1
    # ``observe`` adds an audit tag.
    assert "protbfn_observed" in endpoint_bundle.provenance


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------


def test_determinism(protbfn_adapter: object) -> None:
    """Two calls with the same seed produce byte-identical endpoint digests."""
    bundle1 = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-4", sample_id="sample-protbfn-4"
    )
    bundle2 = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-4", sample_id="sample-protbfn-4"
    )
    assert _hash_bundle(bundle1) == _hash_bundle(bundle2)
    delta = _make_condition_delta(target_round=0, num_steps=4)
    trace1 = protbfn_adapter.solve_ode(bundle1, delta, seed=0)
    trace2 = protbfn_adapter.solve_ode(bundle1, delta, seed=0)
    assert trace1.native_state_digest == trace2.native_state_digest
    assert trace1.integrator_config_hash == trace2.integrator_config_hash
    # Two independent builds of the same input also produce the same
    # initial-state digest.
    digest1 = bundle1.native_state_digest
    digest2 = bundle2.native_state_digest
    assert digest1 == digest2


# ---------------------------------------------------------------------------
# 6. Velocity field / torch lazy-load
# ---------------------------------------------------------------------------


def test_velocity_field_lazy_loads_torch_if_required(
    tmp_path: Path,
) -> None:
    """``force_mode='torch'`` raises if torch is missing or weights absent.

    In ``synthetic`` mode (the default) torch is NOT imported on the
    adapter-side path. We construct a fresh adapter and exercise
    ``build_initial_state`` / ``solve_ode`` end-to-end without ever
    invoking torch.
    """
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ProtBFNAbBFNAdapter,
        torch_is_available,
    )

    adapter = ProtBFNAbBFNAdapter(
        checkpoint_path=None,
        mechanism="ProtBFN",
        force_mode="synthetic",
        num_steps=2,
        max_seq_length=4,
        vocab_size=22,
    )
    bundle = adapter.build_initial_state(
        batch_id="batch-protbfn-5", sample_id="sample-protbfn-5"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    trace = adapter.solve_ode(bundle, delta, seed=0)
    traj = _trajectory_from_trace(adapter, trace)
    assert np.all(np.isfinite(traj))

    # When torch is unavailable, ``force_mode='torch'`` must raise
    # ``RuntimeError``; when torch is available but the file is absent
    # it must raise ``FileNotFoundError``.
    if torch_is_available():
        with pytest.raises(FileNotFoundError):
            ProtBFNAbBFNAdapter(
                checkpoint_path=tmp_path / "missing.pt",
                mechanism="ProtBFN",
                force_mode="torch",
            )
    else:
        with pytest.raises(RuntimeError):
            ProtBFNAbBFNAdapter(
                checkpoint_path=tmp_path / "missing.pt",
                mechanism="ProtBFN",
                force_mode="torch",
            )


# ---------------------------------------------------------------------------
# 7. mechanism_id reflects the loaded checkpoint
# ---------------------------------------------------------------------------


def test_mechanism_id_per_checkpoint() -> None:
    """``mechanism_id`` returns ``ProtBFN`` / ``AbBFN`` / ``AbBFN2`` per arg."""
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ProtBFNAbBFNAdapter,
    )

    a1 = ProtBFNAbBFNAdapter(
        mechanism="ProtBFN", force_mode="synthetic", num_steps=2
    )
    a2 = ProtBFNAbBFNAdapter(
        mechanism="AbBFN", force_mode="synthetic", num_steps=2
    )
    a3 = ProtBFNAbBFNAdapter(
        mechanism="AbBFN2", force_mode="synthetic", num_steps=2
    )
    assert a1.mechanism_id == "ProtBFN"
    assert a2.mechanism_id == "AbBFN"
    assert a3.mechanism_id == "AbBFN2"


# ---------------------------------------------------------------------------
# 8. compose_condition validates inpainting fields
# ---------------------------------------------------------------------------


def test_compose_condition_validates_inpainting(
    protbfn_adapter: object,
) -> None:
    """``compose_condition`` validates inpainting fields; bad inputs raise."""
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-6", sample_id="sample-protbfn-6"
    )
    delta = _make_condition_delta(
        target_round=0,
        extra={
            "inpaint_positions": [1, 3, 5],
            "inpaint_strength": 0.7,
            "n_particles": 8,
            "num_steps": 2,
        },
    )
    composed = protbfn_adapter.compose_condition(bundle, delta)
    assert composed.delta_spec["model_family"] == "ProtBFN"
    assert composed.delta_spec["vocab_size"] == 22
    assert composed.delta_spec["inpaint_strength"] == 0.7
    assert composed.delta_spec["inpaint_positions"] == (1, 3, 5)
    assert composed.delta_spec["n_particles"] == 8

    # Bad inpaint_positions: out-of-range index.
    bad = _make_condition_delta(
        target_round=0, extra={"inpaint_positions": [0, 999]}
    )
    with pytest.raises(ValueError, match="protbfn_inpaint_positions_invalid"):
        protbfn_adapter.compose_condition(bundle, bad)
    # Bad inpaint_strength: outside [0, 1].
    bad = _make_condition_delta(target_round=0, extra={"inpaint_strength": 1.5})
    with pytest.raises(ValueError, match="protbfn_inpaint_strength_invalid"):
        protbfn_adapter.compose_condition(bundle, bad)
    # Bad n_particles: zero / negative.
    bad = _make_condition_delta(target_round=0, extra={"n_particles": 0})
    with pytest.raises(ValueError, match="protbfn_n_particles_invalid"):
        protbfn_adapter.compose_condition(bundle, bad)
    # Bad num_steps: zero / negative.
    bad = _make_condition_delta(target_round=0, extra={"num_steps": 0})
    with pytest.raises(ValueError, match="protbfn_num_steps_must_be_positive"):
        protbfn_adapter.compose_condition(bundle, bad)


# ---------------------------------------------------------------------------
# 9. Restart blend respects the memory fraction
# ---------------------------------------------------------------------------


def test_restart_blend_respects_memory_fraction(
    protbfn_adapter: object,
) -> None:
    """``apply_restart_distribution`` for ``beta in {0.0, 0.5, 1.0}``."""
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-7", sample_id="sample-protbfn-7"
    )
    prior_theta = _native_theta(protbfn_adapter, bundle.native_state_digest)
    L, K = prior_theta.shape
    for beta in (0.0, 0.5, 1.0):
        policy = _make_final_policy(
            policy_id=f"policy-protbfn-7-{beta}",
            run_id="run-protbfn-7",
            beta=beta,
            target_round=0,
        )
        new_bundle = protbfn_adapter.apply_restart_distribution(
            bundle, policy
        )
        new_theta = _native_theta(
            protbfn_adapter, new_bundle.native_state_digest
        )
        assert new_theta.shape == (L, K)
        # The blended theta is a valid probability distribution.
        np.testing.assert_allclose(
            new_theta.sum(axis=1), np.ones(L), atol=1e-12
        )
        assert np.all(new_theta >= 0.0)
        # The audit tag is always appended.
        assert "protbfn_restart_blend" in new_bundle.provenance


# ---------------------------------------------------------------------------
# 10. inject_forward_noise hook
# ---------------------------------------------------------------------------


def test_inject_forward_noise_hook(protbfn_adapter: object) -> None:
    """``inject_forward_noise`` perturbs the categorical and tags provenance."""
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-8", sample_id="sample-protbfn-8"
    )
    L, K = (
        int(protbfn_adapter._max_seq_length),  # noqa: SLF001
        int(protbfn_adapter._vocab_size),  # noqa: SLF001
    )
    rng = np.random.default_rng(13)
    injected = rng.random((L, K)).astype(np.float64)
    injected = injected / injected.sum(axis=1, keepdims=True)
    new_bundle = protbfn_adapter.inject_forward_noise(bundle, injected)
    new_theta = _native_theta(
        protbfn_adapter, new_bundle.native_state_digest
    )
    # The hook tags the provenance.
    assert "forward_noise_applied" in new_bundle.provenance
    # The result is finite and a valid probability distribution.
    assert np.all(np.isfinite(new_theta))
    np.testing.assert_allclose(
        new_theta.sum(axis=1), np.ones(L), atol=1e-12
    )


# ---------------------------------------------------------------------------
# 11. Adapter satisfies the @runtime_checkable Protocol
# ---------------------------------------------------------------------------


def test_adapter_satisfies_protocol(protbfn_adapter: object) -> None:
    """Adapter passes the runtime-checkable Protocol check."""
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    assert isinstance(protbfn_adapter, FlowMatchingODEAdapter)


# ---------------------------------------------------------------------------
# 12. Engine.run_round drives an end-to-end round
# ---------------------------------------------------------------------------


def test_run_round_produces_sequence_endpoint(
    protbfn_adapter: object,
) -> None:
    """``Engine.run_round`` drives an end-to-end round; endpoint is finite."""
    from adaptive_reflow.frame import Engine

    engine = Engine()
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-9", sample_id="sample-protbfn-9"
    )
    policy = _make_final_policy(
        policy_id="policy-protbfn-9",
        run_id="run-protbfn-9",
        beta=0.5,
        target_round=0,
    )
    delta = _make_condition_delta(target_round=0, num_steps=4)
    result = engine.run_round(
        round_index=0,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=protbfn_adapter,
        policy=policy,
        condition_delta=delta,
    )
    trace = result.round_trace
    assert trace.integrator_trace is not None
    endpoint_bundle = protbfn_adapter.observe_endpoint(
        trace.integrator_trace, bundle
    )
    theta = _native_theta(
        protbfn_adapter, endpoint_bundle.native_state_digest
    )
    L, K = theta.shape
    assert np.all(np.isfinite(theta))
    np.testing.assert_allclose(
        theta.sum(axis=1), np.ones(L), atol=1e-12
    )


# ---------------------------------------------------------------------------
# 13. Engine stress - 20 rounds alternating beta
# ---------------------------------------------------------------------------


def test_engine_stress_20_rounds_with_restart(
    protbfn_adapter: object,
) -> None:
    """``Engine.run_round`` drives 20 rounds alternating ``beta``; no NaN."""
    from adaptive_reflow.frame import Engine

    engine = Engine()
    start = time.perf_counter()
    bundle = protbfn_adapter.build_initial_state(
        batch_id="batch-protbfn-10", sample_id="sample-protbfn-10"
    )
    b = bundle
    for r in range(20):
        policy = _make_final_policy(
            policy_id=f"policy-protbfn-10-{r}",
            run_id="run-protbfn-10",
            beta=(0.5 if r % 2 == 0 else 0.0),
            target_round=r,
        )
        delta = _make_condition_delta(target_round=r, num_steps=2)
        result = engine.run_round(
            round_index=r,
            phase_state=_make_phase_state(),
            bundle=b,
            adapter=protbfn_adapter,
            policy=policy,
            condition_delta=delta,
        )
        trace = result.round_trace
        assert trace.integrator_trace is not None
        endpoint_bundle = protbfn_adapter.observe_endpoint(
            trace.integrator_trace, b
        )
        theta = _native_theta(
            protbfn_adapter, endpoint_bundle.native_state_digest
        )
        assert np.all(np.isfinite(theta))
        b = endpoint_bundle
    elapsed = time.perf_counter() - start
    # Synthetic mode is NumPy-only and very fast; 20 rounds must finish
    # well under 60 seconds even on the slowest CI box.
    assert elapsed < 60.0, f"stress run blew budget: {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# 14. AbBFN / AbBFN2 factory
# ---------------------------------------------------------------------------


def test_default_factory_per_mechanism() -> None:
    """``default_protbfnabbfn_adapter`` per-mechanism defaults are correct."""
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ABBFN_DEFAULT_NUM_STEPS,
        ABBFN_MAX_LENGTH,
        PROTBFN_DEFAULT_NUM_STEPS,
        PROTBFN_MAX_LENGTH,
        default_protbfnabbfn_adapter,
    )

    a_protbfn = default_protbfnabbfn_adapter(
        mechanism="ProtBFN", force_mode="synthetic"
    )
    a_abbfn = default_protbfnabbfn_adapter(
        mechanism="AbBFN", force_mode="synthetic"
    )
    a_abbfn2 = default_protbfnabbfn_adapter(
        mechanism="AbBFN2", force_mode="synthetic"
    )
    assert a_protbfn._num_steps == PROTBFN_DEFAULT_NUM_STEPS  # noqa: SLF001
    assert a_protbfn._max_seq_length == PROTBFN_MAX_LENGTH  # noqa: SLF001
    assert a_abbfn._num_steps == ABBFN_DEFAULT_NUM_STEPS  # noqa: SLF001
    assert a_abbfn._max_seq_length == ABBFN_MAX_LENGTH  # noqa: SLF001
    assert a_abbfn2._max_seq_length == ABBFN_MAX_LENGTH  # noqa: SLF001
    assert a_protbfn.mechanism_id == "ProtBFN"
    assert a_abbfn.mechanism_id == "AbBFN"
    assert a_abbfn2.mechanism_id == "AbBFN2"


# ---------------------------------------------------------------------------
# 15. force_mode allowlist accepts "upstream_jax"
# ---------------------------------------------------------------------------


def test_force_mode_upstream_jax_in_allowlist() -> None:
    """``force_mode='upstream_jax'`` is a valid value in the Mode Literal.

    Verifies the type system accepted the new member and that a fresh
    adapter constructed in synthetic mode reports its mode verbatim.
    The full upstream-jax materialization path requires the JAX stack
    + a real checkpoint directory; we do NOT exercise that here (the
    harness-level smoke covers it under ``--use-jax-loader``).
    """
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        Mode,
        ProtBFNAbBFNAdapter,
    )

    # 1. ``Mode`` literal exposes the new value (static type-level check).
    assert "upstream_jax" in Mode.__args__

    # 2. ``force_mode='upstream_jax'`` constructs an adapter without
    #    raising under ``is_upstream_available() == True`` (which is the
    #    case in the protbfn_venv where jax + dm-haiku + flax are
    #    installed). We only verify the allowlist accepts the value;
    #    we do NOT exercise ``solve_ode`` here (would require GPU and
    #    the upstream pytree -> JAX pytree binding, which is a separate
    #    workflow).
    from adaptive_reflow.adapters.protbfn_abbfn_upstream_shim import (
        is_upstream_available,
    )

    if is_upstream_available():
        ckpt = Path(
            "/home/hugo/codes/flowa-multistep-reinference/data/protbfn_abbfn/weights_real/ProtBFN"
        )
        if ckpt.is_dir() and (ckpt / "tree_def.npy").is_file():
            a = ProtBFNAbBFNAdapter(
                checkpoint_path=ckpt,
                mechanism="ProtBFN",
                force_mode="upstream_jax",
                num_steps=2,
                max_seq_length=4,
                vocab_size=22,
            )
            assert a._mode == "upstream_jax"  # noqa: SLF001
            assert a._mechanism == "ProtBFN"  # noqa: SLF001

    # 3. ``force_mode='upstream_jax'`` raises RuntimeError when the
    #    JAX stack is unavailable. We simulate this by stubbing the
    #    upstream availability check.
    from unittest.mock import patch

    from adaptive_reflow.adapters import protbfn_abbfn_upstream_shim as shim

    with patch.object(shim, "is_upstream_available", return_value=False):
        with pytest.raises(RuntimeError, match="upstream_jax_requested"):
            ProtBFNAbBFNAdapter(
                mechanism="ProtBFN",
                force_mode="upstream_jax",
                num_steps=2,
                max_seq_length=4,
            )
