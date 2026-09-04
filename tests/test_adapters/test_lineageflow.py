"""Smoke test suite for the LineageFlow protein flow-matching adapter (Wave 10).

Mirrors :mod:`tests.test_adapters.test_self_flow`'s structure for the
LineageFlow ESM-2 + flow-head adapter. Tests exercise the load-bearing
:class:`FlowMatchingODEAdapter` Protocol contract, the
``build_initial_state`` / ``solve_ode`` / ``observe_endpoint`` loop,
the per-position categorical restart blending, and the
synthetic-mode determinism invariant.

22 tests; all CPU-runnable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.lineageflow import (
    AMINO_ACID_CATEGORICAL,
    AUDIT_FORWARD_NOISE_APPLIED,
    AUDIT_LINEAGEFLOW_OBSERVED,
    AUDIT_LINEAGEFLOW_RESTART_BLEND,
    ERR_LINEAGEFLOW_FAMILY_ID_INVALID,
    ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN,
    ERR_LINEAGEFLOW_L_OUT_OF_RANGE,
    ERR_LINEAGEFLOW_NUM_STEPS,
    ERR_LINEAGEFLOW_VOCAB_OUT_OF_RANGE,
    LINEAGEFLOW_CFG_SCALE_DEFAULT,
    LINEAGEFLOW_CHANNELS,
    LINEAGEFLOW_CLAMP,
    LINEAGEFLOW_CONFIG_HASH,
    LINEAGEFLOW_FAMILY_ID_DEFAULT,
    LINEAGEFLOW_INTEGRATORS,
    LINEAGEFLOW_INTEGRATOR_EULER,
    LINEAGEFLOW_INTEGRATOR_HEUN,
    LINEAGEFLOW_MECHANISM_ID,
    LINEAGEFLOW_MAX_LENGTH,
    LINEAGEFLOW_NUM_STEPS_DEFAULT,
    LINEAGEFLOW_STATE_SHAPE,
    LINEAGEFLOW_T_END,
    LINEAGEFLOW_VOCAB_SIZE,
    LineageFlowAdapter,
    LineageFlowCapabilities,
    PFAM_FAMILY_COND,
    default_lineageflow_adapter,
    lineageflow_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    StateBundle,
    validate_state_bundle,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    RunId,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(*, force_mode: str = "synthetic", **kwargs) -> LineageFlowAdapter:
    """Build a synthetic-mode adapter for protocol-surface tests."""
    return LineageFlowAdapter(force_mode=force_mode, **kwargs)


def _make_delta(
    *,
    source: str = "test",
    target_round: int = 1,
    calibration_artifact_hash: str = LINEAGEFLOW_CONFIG_HASH,
    **spec: object,
) -> ODEConditionDelta:
    """Build an :class:`ODEConditionDelta` with sensible defaults."""
    base: dict[str, object] = {
        "num_steps": 4,
        "sampler_id": LINEAGEFLOW_INTEGRATOR_EULER,
        "guidance_scale": LINEAGEFLOW_CFG_SCALE_DEFAULT,
        "family_id": "PF00001.21",
    }
    base.update(spec)
    return ODEConditionDelta(
        delta_spec=base,  # type: ignore[arg-type]
        source=source,
        target_round=target_round,
        calibration_artifact_hash=calibration_artifact_hash,
    )


# ---------------------------------------------------------------------------
# Capability / construction
# ---------------------------------------------------------------------------


def test_capabilities_handshake() -> None:
    adapter = _make_adapter()
    caps = adapter.capabilities()
    assert caps.has_ode_integration_surface
    assert caps.has_prior_export
    assert caps.has_state_export
    assert caps.has_condition_injection
    assert caps.has_restart_boundary
    assert caps.has_continuous_channels
    assert caps.has_discrete_channels
    assert caps.has_trajectory_digest
    assert caps.has_deterministic_seed
    assert caps.state_shape == LINEAGEFLOW_STATE_SHAPE
    assert caps.supported_channels == LINEAGEFLOW_CHANNELS
    assert caps.native_config_hash == LINEAGEFLOW_CONFIG_HASH
    # Channel-domain declaration is required to be coherent.
    for name in caps.supported_channels:
        assert name in caps.channel_domains
    # The amino_acid_categorical channel is declared as
    # ``"discrete"``-domain.
    assert (
        caps.channel_domains[AMINO_ACID_CATEGORICAL] == "discrete"
    )
    # The pfam_family_cond channel is declared as
    # ``"continuous"``-domain.
    assert caps.channel_domains[PFAM_FAMILY_COND] == "continuous"


def test_protocol_satisfies_runtime_checkable() -> None:
    adapter = _make_adapter()
    assert isinstance(adapter, FlowMatchingODEAdapter)


def test_state_shape_advertised_matches_runner() -> None:
    adapter = _make_adapter()
    assert adapter.state_shape == LINEAGEFLOW_STATE_SHAPE
    assert adapter.capabilities().state_shape == LINEAGEFLOW_STATE_SHAPE
    assert LINEAGEFLOW_STATE_SHAPE == (LINEAGEFLOW_MAX_LENGTH, LINEAGEFLOW_VOCAB_SIZE)


def test_synthetic_mode_no_weights_required() -> None:
    """Adapter constructs without weights when force_mode='synthetic'."""
    adapter = LineageFlowAdapter(
        force_mode="synthetic",
        weights_path=Path("/nonexistent/weights.ckpt"),
    )
    assert adapter._mode == "synthetic"
    assert adapter._synthetic_weights is not None


def test_unknown_solver_rejected() -> None:
    with pytest.raises(ValueError, match=ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN):
        LineageFlowAdapter(solver="rk45")  # type: ignore[arg-type]


def test_num_steps_must_be_positive() -> None:
    with pytest.raises(ValueError, match=ERR_LINEAGEFLOW_NUM_STEPS):
        LineageFlowAdapter(num_steps=0)


def test_invalid_family_id_rejected() -> None:
    with pytest.raises(ValueError, match=ERR_LINEAGEFLOW_FAMILY_ID_INVALID):
        LineageFlowAdapter(family_id="")


# ---------------------------------------------------------------------------
# Protocol surface
# ---------------------------------------------------------------------------


def test_build_initial_state_returns_correct_shape() -> None:
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(
        batch_id="b0", sample_id="s0",
    )
    ok, errs = validate_state_bundle(bundle)
    assert ok, errs
    assert bundle.source_round == 0
    assert bundle.detach_proof is True
    assert bundle.native_state_digest
    assert LINEAGEFLOW_MECHANISM_ID in bundle.provenance

    # The native state must resolve to a
    # ``(max_seq_length, vocab_size)`` array.
    entry = adapter._native_states[bundle.native_state_digest]
    theta = np.asarray(entry["theta"], dtype=np.float64)
    assert theta.shape == LINEAGEFLOW_STATE_SHAPE
    assert np.isfinite(theta).all()
    # Each row must be a valid per-position probability
    # distribution (sums to 1).
    row_sums = theta.sum(axis=-1)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-9)


def test_solve_ode_returns_finite_trace() -> None:
    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="b1", sample_id="s1")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    assert trace.steps == 4
    assert 0.0 <= trace.accept_rate <= 1.0
    assert trace.native_state_digest
    assert trace.integrator_config_hash

    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (5, *LINEAGEFLOW_STATE_SHAPE)
    assert np.isfinite(traj).all()
    # Per-position probabilities must stay within the clamp envelope
    # and remain valid probability distributions (row sums to 1).
    assert np.abs(traj).max() <= LINEAGEFLOW_CLAMP + 1e-9
    np.testing.assert_allclose(
        traj.sum(axis=-1), 1.0, atol=1e-9,
    )


def test_endpoint_round_trip() -> None:
    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="b2", sample_id="s2")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)
    endpoint = adapter.observe_endpoint(trace, bundle)

    ok, errs = validate_state_bundle(endpoint)
    assert ok, errs
    assert endpoint.source_round == bundle.source_round + 1
    assert endpoint.detach_proof is True
    assert AUDIT_LINEAGEFLOW_OBSERVED in endpoint.provenance

    entry = adapter._native_states[endpoint.native_state_digest]
    theta_final = np.asarray(entry["theta"], dtype=np.float64)
    assert theta_final.shape == LINEAGEFLOW_STATE_SHAPE
    assert np.isfinite(theta_final).all()
    np.testing.assert_allclose(
        theta_final.sum(axis=-1), 1.0, atol=1e-9,
    )


def test_determinism() -> None:
    """Two solve_ode calls from identical inputs are byte-identical."""
    adapter_a = _make_adapter(num_steps=4)
    adapter_b = _make_adapter(num_steps=4)
    bundle_a = adapter_a.build_initial_state(batch_id="b3", sample_id="s3")
    bundle_b = adapter_b.build_initial_state(batch_id="b3", sample_id="s3")
    delta_a = _make_delta(target_round=1)
    delta_b = _make_delta(target_round=1)
    delta_a = adapter_a.compose_condition(bundle_a, delta_a)
    delta_b = adapter_b.compose_condition(bundle_b, delta_b)
    trace_a = adapter_a.solve_ode(bundle_a, delta_a, seed=7)
    trace_b = adapter_b.solve_ode(bundle_b, delta_b, seed=7)
    traj_a = adapter_a.export_trajectory(trace_a)
    traj_b = adapter_b.export_trajectory(trace_b)
    assert traj_a is not None and traj_b is not None
    np.testing.assert_array_equal(traj_a, traj_b)


# ---------------------------------------------------------------------------
# Condition injection
# ---------------------------------------------------------------------------


def test_compose_condition_injects_family_id_and_cfg() -> None:
    adapter = _make_adapter(num_steps=8, family_id="PF00002.30")
    bundle = adapter.build_initial_state(batch_id="b4", sample_id="s4")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)

    # explicit family_id override wins
    assert delta.delta_spec["family_id"] == "PF00001.21"
    assert delta.delta_spec["num_steps"] == 4  # from delta
    assert delta.delta_spec["sampler_id"] == LINEAGEFLOW_INTEGRATOR_EULER
    assert "guidance_scale" in delta.delta_spec
    assert "conditioning_cache_hash" in delta.delta_spec
    cache_hash = str(delta.delta_spec["conditioning_cache_hash"])
    assert cache_hash in adapter._conditioning_cache


def test_compose_condition_rejects_invalid_sampler() -> None:
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="b5", sample_id="s5")
    delta = _make_delta(target_round=1, sampler_id="bogus_solver")
    with pytest.raises(ValueError, match=ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN):
        adapter.compose_condition(bundle, delta)


# ---------------------------------------------------------------------------
# Restart / detachment / inject_forward_noise
# ---------------------------------------------------------------------------


def test_apply_restart_preserves_conditioning() -> None:
    adapter = _make_adapter(num_steps=2)
    bundle = adapter.build_initial_state(batch_id="b6", sample_id="s6")
    policy = FinalRestartPolicy(
        policy_id=PolicyId("uniform-beta-0.5"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("test-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.5)},
        alpha_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(1.0)},
        fresh_noise_floor_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={AMINO_ACID_CATEGORICAL: True},
        ledger_row_id=LedgerRowId("ledger-uniform-beta-0.5"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    restarted = adapter.apply_restart_distribution(bundle, policy)

    ok, errs = validate_state_bundle(restarted)
    assert ok, errs
    assert restarted.source_round == bundle.source_round + 1
    assert AUDIT_LINEAGEFLOW_RESTART_BLEND in restarted.provenance

    # Conditioning reference must propagate forward so the
    # family-encoder cache is reused.
    original_cond = bundle.channels[PFAM_FAMILY_COND]
    restarted_cond = restarted.channels[PFAM_FAMILY_COND]
    assert original_cond == restarted_cond

    # The blended per-position distribution must be a valid
    # probability distribution (row sums to 1).
    entry = adapter._native_states[restarted.native_state_digest]
    blended = np.asarray(entry["theta"], dtype=np.float64)
    assert blended.shape == LINEAGEFLOW_STATE_SHAPE
    np.testing.assert_allclose(
        blended.sum(axis=-1), 1.0, atol=1e-9,
    )


def test_export_trajectory_returns_native() -> None:
    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="b7", sample_id="s7")
    delta = _make_delta(target_round=1, num_steps=3)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, *LINEAGEFLOW_STATE_SHAPE)
    assert np.isfinite(traj).all()

    # An unknown digest returns None (not raise).
    from adaptive_reflow.universal.state import ODEIntegratorTrace
    bogus_trace = ODEIntegratorTrace(
        steps=1, accept_rate=1.0,
        native_state_digest="bogus", integrator_config_hash="bogus",
    )
    assert adapter.export_trajectory(bogus_trace) is None


def test_inject_forward_noise_hook() -> None:
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="b8", sample_id="s8")
    rng = np.random.default_rng(0)
    noise = _synthesize_noise_like_tensor(rng)
    new_bundle = adapter.inject_forward_noise(bundle, noise)

    ok, errs = validate_state_bundle(new_bundle)
    assert ok, errs
    assert AUDIT_FORWARD_NOISE_APPLIED in new_bundle.provenance
    entry = adapter._native_states[new_bundle.native_state_digest]
    theta_new = np.asarray(entry["theta"], dtype=np.float64)
    assert theta_new.shape == LINEAGEFLOW_STATE_SHAPE
    # The forward-noise path must produce a valid probability
    # distribution (row sums to 1).
    np.testing.assert_allclose(
        theta_new.sum(axis=-1), 1.0, atol=1e-9,
    )


def _synthesize_noise_like_tensor(rng: np.random.Generator) -> np.ndarray:
    """Helper: a (L, K) per-position categorical that sums to 1 per row."""
    theta = rng.uniform(0.0, 1.0, size=LINEAGEFLOW_STATE_SHAPE).astype(
        np.float64
    )
    theta = theta / theta.sum(axis=-1, keepdims=True)
    return theta


# ---------------------------------------------------------------------------
# Heun + registry + helpers
# ---------------------------------------------------------------------------


def test_heun_solver_round_trip() -> None:
    adapter = LineageFlowAdapter(
        force_mode="synthetic",
        solver=LINEAGEFLOW_INTEGRATOR_HEUN,
        num_steps=3,
    )
    assert adapter._solver == LINEAGEFLOW_INTEGRATOR_HEUN
    bundle = adapter.build_initial_state(batch_id="b9", sample_id="s9")
    delta = _make_delta(
        target_round=1, sampler_id=LINEAGEFLOW_INTEGRATOR_HEUN, num_steps=3,
    )
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=99)
    assert trace.steps == 3
    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, *LINEAGEFLOW_STATE_SHAPE)
    assert np.isfinite(traj).all()
    np.testing.assert_allclose(
        traj.sum(axis=-1), 1.0, atol=1e-9,
    )


def test_registry_includes_lineageflow() -> None:
    from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter
    assert "lineageflow" in ADAPTER_REGISTRY
    adapter = build_adapter("lineageflow", force_mode="synthetic")
    assert isinstance(adapter, LineageFlowAdapter)
    assert adapter._mode == "synthetic"


def test_default_factory_signature() -> None:
    adapter = default_lineageflow_adapter(force_mode="synthetic")
    assert isinstance(adapter, LineageFlowAdapter)
    assert adapter._mode == "synthetic"
    assert adapter._num_steps == LINEAGEFLOW_NUM_STEPS_DEFAULT
    assert adapter._solver == LINEAGEFLOW_INTEGRATOR_EULER
    assert adapter._family_id == LINEAGEFLOW_FAMILY_ID_DEFAULT


def test_resolve_weights_path_finds_published_ckpt() -> None:
    """Resolves the actually-downloaded checkpoint, or returns None cleanly."""
    p = lineageflow_resolve_weights_path()
    if p is not None:
        assert p.name == "lineageflow-rp55.ckpt"
        assert p.exists()


def test_torch_is_available_smoke() -> None:
    """``torch_is_available`` returns a bool without raising."""
    assert isinstance(torch_is_available(), bool)


def test_mechanism_id_matches_class_attribute() -> None:
    adapter = _make_adapter()
    assert adapter.mechanism_id == LINEAGEFLOW_MECHANISM_ID
