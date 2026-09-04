"""Smoke test suite for the Self-Flow latent flow-matching adapter (Wave 9).

Mirrors :mod:`tests.test_adapters.test_hidream_i1`'s structure but at
a smaller scope — the Wave 9 deliverable is a design-skeleton
adapter, not a 22-test surface. Tests exercise the load-bearing
:class:`FlowMatchingODEAdapter` Protocol contract, the
``build_initial_state`` / ``solve_ode`` / ``observe_endpoint``
loop, the latent-state restart blending, and the synthetic-mode
determinism invariant.

Tests:

* ``test_capabilities_handshake`` — adapter constructs; capability
  surface is well-formed (state_shape, channels, domain tags).
* ``test_build_initial_state_returns_correct_shape`` —
  ``build_initial_state`` produces a bundle whose latent TensorRef
  resolves to a ``(4, 32, 32)`` array.
* ``test_solve_ode_returns_finite_trace`` — ``solve_ode`` returns a
  finite trajectory over ``num_steps`` Euler steps.
* ``test_endpoint_round_trip`` — ``observe_endpoint`` returns a
  bundle whose ``native_state_digest`` resolves to a finite
  ``(4, 32, 32)`` array.
* ``test_determinism`` — two ``solve_ode`` calls from identical
  inputs are byte-identical.
* ``test_protocol_satisfies_runtime_checkable`` —
  :class:`SelfFlowAdapter` passes the ``@runtime_checkable`` Protocol
  check via ``isinstance``.
* ``test_state_shape_advertised_matches_runner`` —
  ``capabilities().state_shape == (4, 32, 32)`` so the runner's
  forward-noise allocation matches.
* ``test_compose_condition_injects_class_label_and_cfg`` —
  :meth:`compose_condition` resolves the class label + guidance_scale
  + num_steps + sampler_id defaults and writes the conditioning
  cache hash back into the ``delta_spec``.
* ``test_compose_condition_rejects_invalid_class_label`` —
  :meth:`compose_condition` raises when the class label is out of
  range.
* ``test_apply_restart_preserves_conditioning`` — the
  ``class_cond`` TensorRef is preserved across the restart boundary
  so the cache is reused.
* ``test_synthetic_mode_no_weights_required`` — adapter constructs in
  synthetic mode without the weights file and ``force_mode='synthetic'``.
* ``test_export_trajectory_returns_native`` —
  :meth:`export_trajectory` returns the native trajectory stored
  under the trace's ``native_state_digest``.
* ``test_inject_forward_noise_hook`` —
  :meth:`inject_forward_noise` adds the perturbation and tags the
  provenance.
* ``test_unknown_solver_rejected`` — the constructor rejects unknown
  solver names with a deterministic error code.
* ``test_registry_includes_self_flow`` — the
  :data:`ADAPTER_REGISTRY` exposes the family name.
* ``test_heun_solver_round_trip`` — ``solver='heun'`` accepts and
  produces a finite trajectory.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.self_flow import (
    AUDIT_FORWARD_NOISE_APPLIED,
    AUDIT_SELF_FLOW_OBSERVED,
    AUDIT_SELF_FLOW_RESTART_BLEND,
    ERR_SELF_FLOW_CLASS_LABEL_INVALID,
    ERR_SELF_FLOW_INTEGRATOR_UNKNOWN,
    ERR_SELF_FLOW_NUM_STEPS,
    SELF_FLOW_CFG_SCALE_DEFAULT,
    SELF_FLOW_CHANNELS,
    SELF_FLOW_CLAMP,
    SELF_FLOW_CONFIG_HASH,
    SELF_FLOW_INTEGRATORS,
    SELF_FLOW_INTEGRATOR_EULER,
    SELF_FLOW_INTEGRATOR_HEUN,
    SELF_FLOW_MECHANISM_ID,
    SELF_FLOW_NUM_STEPS_DEFAULT,
    SELF_FLOW_STATE_SHAPE,
    SELF_FLOW_T_END,
    SelfFlowAdapter,
    SelfFlowCapabilities,
    default_self_flow_adapter,
    self_flow_resolve_weights_path,
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


def _make_adapter(*, force_mode: str = "synthetic", **kwargs) -> SelfFlowAdapter:
    """Build a synthetic-mode adapter for protocol-surface tests."""
    return SelfFlowAdapter(force_mode=force_mode, **kwargs)


def _make_delta(
    *,
    source: str = "test",
    target_round: int = 1,
    calibration_artifact_hash: str = SELF_FLOW_CONFIG_HASH,
    **spec: object,
) -> ODEConditionDelta:
    """Build an :class:`ODEConditionDelta` with sensible defaults."""
    base: dict[str, object] = {
        "num_steps": 4,
        "sampler_id": SELF_FLOW_INTEGRATOR_EULER,
        "guidance_scale": SELF_FLOW_CFG_SCALE_DEFAULT,
        "class_label": 207,  # "golden retriever"
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
    assert caps.has_trajectory_digest
    assert caps.has_deterministic_seed
    assert caps.state_shape == SELF_FLOW_STATE_SHAPE
    assert caps.supported_channels == SELF_FLOW_CHANNELS
    assert caps.native_config_hash == SELF_FLOW_CONFIG_HASH
    # Channel-domain declaration is required to be coherent.
    for name in caps.supported_channels:
        assert name in caps.channel_domains
    # The image_latent channel is declared as ``"latent"``-domain.
    assert caps.channel_domains[ChannelName("image_latent")] == "latent"
    # The class_cond channel is declared as ``"continuous"``-domain.
    assert caps.channel_domains[ChannelName("class_cond")] == "continuous"


def test_protocol_satisfies_runtime_checkable() -> None:
    adapter = _make_adapter()
    assert isinstance(adapter, FlowMatchingODEAdapter)


def test_state_shape_advertised_matches_runner() -> None:
    adapter = _make_adapter()
    assert adapter.state_shape == SELF_FLOW_STATE_SHAPE
    assert adapter.capabilities().state_shape == SELF_FLOW_STATE_SHAPE
    assert SELF_FLOW_STATE_SHAPE == (4, 32, 32)


def test_synthetic_mode_no_weights_required() -> None:
    """Adapter constructs without weights when force_mode='synthetic'."""
    adapter = SelfFlowAdapter(
        force_mode="synthetic",
        weights_path=Path("/nonexistent/weights.pt"),
    )
    assert adapter._mode == "synthetic"
    assert adapter._synthetic_weights is not None


def test_unknown_solver_rejected() -> None:
    with pytest.raises(ValueError, match=ERR_SELF_FLOW_INTEGRATOR_UNKNOWN):
        SelfFlowAdapter(solver="rk45")  # type: ignore[arg-type]


def test_num_steps_must_be_positive() -> None:
    with pytest.raises(ValueError, match=ERR_SELF_FLOW_NUM_STEPS):
        SelfFlowAdapter(num_steps=0)


def test_invalid_class_label_rejected() -> None:
    with pytest.raises(ValueError, match=ERR_SELF_FLOW_CLASS_LABEL_INVALID):
        SelfFlowAdapter(class_label=-1)
    with pytest.raises(ValueError, match=ERR_SELF_FLOW_CLASS_LABEL_INVALID):
        SelfFlowAdapter(class_label=2000)


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
    assert bundle.state_shape == SELF_FLOW_STATE_SHAPE if hasattr(bundle, "state_shape") else True
    assert bundle.source_round == 0
    assert bundle.detach_proof is True
    assert bundle.native_state_digest
    assert SELF_FLOW_MECHANISM_ID in bundle.provenance

    # The native state must resolve to a (4, 32, 32) array.
    entry = adapter._native_states[bundle.native_state_digest]
    x0 = np.asarray(entry["x0"], dtype=np.float64)
    assert x0.shape == SELF_FLOW_STATE_SHAPE
    assert np.isfinite(x0).all()


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
    assert traj.shape == (5, *SELF_FLOW_STATE_SHAPE)
    assert np.isfinite(traj).all()
    # Latent values must stay within the clamp envelope.
    assert np.abs(traj).max() <= SELF_FLOW_CLAMP + 1e-9


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
    assert AUDIT_SELF_FLOW_OBSERVED in endpoint.provenance

    entry = adapter._native_states[endpoint.native_state_digest]
    x_final = np.asarray(entry["x"], dtype=np.float64)
    assert x_final.shape == SELF_FLOW_STATE_SHAPE
    assert np.isfinite(x_final).all()


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


def test_compose_condition_injects_class_label_and_cfg() -> None:
    adapter = _make_adapter(num_steps=8, class_label=42)
    bundle = adapter.build_initial_state(batch_id="b4", sample_id="s4")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)

    assert delta.delta_spec["class_label"] == 207  # explicit override wins
    assert delta.delta_spec["num_steps"] == 4  # from delta
    assert delta.delta_spec["sampler_id"] == SELF_FLOW_INTEGRATOR_EULER
    assert "guidance_scale" in delta.delta_spec
    assert "conditioning_cache_hash" in delta.delta_spec
    cache_hash = str(delta.delta_spec["conditioning_cache_hash"])
    assert cache_hash in adapter._conditioning_cache


def test_compose_condition_rejects_invalid_class_label() -> None:
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="b5", sample_id="s5")
    delta = _make_delta(target_round=1, class_label=5000)
    with pytest.raises(ValueError, match=ERR_SELF_FLOW_CLASS_LABEL_INVALID):
        adapter.compose_condition(bundle, delta)


# ---------------------------------------------------------------------------
# Restart / detachment / inject_forward_noise
# ---------------------------------------------------------------------------


def test_apply_restart_preserves_conditioning() -> None:
    adapter = _make_adapter(num_steps=2)
    bundle = adapter.build_initial_state(batch_id="b6", sample_id="s6")
    channel = ChannelName("image_latent")
    policy = FinalRestartPolicy(
        policy_id=PolicyId("uniform-beta-0.5"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("test-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(0.5)},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId("ledger-uniform-beta-0.5"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    restarted = adapter.apply_restart_distribution(bundle, policy)

    ok, errs = validate_state_bundle(restarted)
    assert ok, errs
    assert restarted.source_round == bundle.source_round + 1
    assert AUDIT_SELF_FLOW_RESTART_BLEND in restarted.provenance

    # Conditioning reference must propagate forward so the
    # class-encoder cache is reused.
    original_cond = bundle.channels[ChannelName("class_cond")]
    restarted_cond = restarted.channels[ChannelName("class_cond")]
    assert original_cond == restarted_cond


def test_export_trajectory_returns_native() -> None:
    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="b7", sample_id="s7")
    delta = _make_delta(target_round=1, num_steps=3)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, *SELF_FLOW_STATE_SHAPE)
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
    noise = np.random.default_rng(0).standard_normal(SELF_FLOW_STATE_SHAPE)
    new_bundle = adapter.inject_forward_noise(bundle, noise)

    ok, errs = validate_state_bundle(new_bundle)
    assert ok, errs
    assert AUDIT_FORWARD_NOISE_APPLIED in new_bundle.provenance
    entry = adapter._native_states[new_bundle.native_state_digest]
    x_new = np.asarray(entry["x0"], dtype=np.float64)
    assert x_new.shape == SELF_FLOW_STATE_SHAPE
    # The forward-noise path must clip to the clamp envelope.
    assert np.abs(x_new).max() <= SELF_FLOW_CLAMP + 1e-9


# ---------------------------------------------------------------------------
# Heun + registry + helpers
# ---------------------------------------------------------------------------


def test_heun_solver_round_trip() -> None:
    adapter = SelfFlowAdapter(
        force_mode="synthetic",
        solver=SELF_FLOW_INTEGRATOR_HEUN,
        num_steps=3,
    )
    assert adapter._solver == SELF_FLOW_INTEGRATOR_HEUN
    bundle = adapter.build_initial_state(batch_id="b9", sample_id="s9")
    delta = _make_delta(
        target_round=1, sampler_id=SELF_FLOW_INTEGRATOR_HEUN, num_steps=3,
    )
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=99)
    assert trace.steps == 3
    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, *SELF_FLOW_STATE_SHAPE)
    assert np.isfinite(traj).all()


def test_registry_includes_self_flow() -> None:
    from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter
    assert "self_flow" in ADAPTER_REGISTRY
    adapter = build_adapter("self_flow", force_mode="synthetic")
    assert isinstance(adapter, SelfFlowAdapter)
    assert adapter._mode == "synthetic"


def test_default_factory_signature() -> None:
    adapter = default_self_flow_adapter(force_mode="synthetic")
    assert isinstance(adapter, SelfFlowAdapter)
    assert adapter._mode == "synthetic"
    assert adapter._num_steps == SELF_FLOW_NUM_STEPS_DEFAULT
    assert adapter._solver == SELF_FLOW_INTEGRATOR_EULER


def test_resolve_weights_path_finds_published_ckpt() -> None:
    """Resolves the actually-downloaded checkpoint, or returns None cleanly."""
    p = self_flow_resolve_weights_path()
    if p is not None:
        assert p.name == "selfflow_imagenet256.pt"
        assert p.exists()


def test_torch_is_available_smoke() -> None:
    """``torch_is_available`` returns a bool without raising."""
    assert isinstance(torch_is_available(), bool)


def test_mechanism_id_matches_class_attribute() -> None:
    adapter = _make_adapter()
    assert adapter.mechanism_id == SELF_FLOW_MECHANISM_ID
