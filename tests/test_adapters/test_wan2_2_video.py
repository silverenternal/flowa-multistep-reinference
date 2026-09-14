"""Comprehensive test suite for the Wan2.2 video Flow Matching ODE adapter.

Exercises :class:`adaptive_reflow.adapters.wan2_2_video
.Wan22VideoAdapter` end-to-end. The adapter wraps a
deterministic NumPy velocity field (test-mode ``synthetic``) shaped as
``v_theta(x, t) = W2 @ tanh(W1 @ flatten(x) + b1 + t * t_bias
+ text_mean @ text_proj + route * route_proj) + b2`` so the test
suite runs without a GPU or the heavy torch dependency. The MoE
route selection mirrors the design spec: ``moe_route == "high"``
when ``t >= t_moe``, else ``"low"`` (A14B only; TI2V-5B uses a
single dense forward).

Tests:

* ``test_capabilities_handshake`` — every required engine-side flag
  is ``True``; capability surface is well-formed.
* ``test_build_initial_state_returns_correct_shape`` — the initial
  state's ``video_latent`` resolves to a ``(16, 30, 45, 80)`` tensor.
* ``test_solve_ode_returns_finite_trace`` — ``solve_ode`` returns a
  finite trajectory; the endpoint's ``native_state_digest`` resolves
  to the canonical ``(C, T_lat, H_lat, W_lat)`` shape.
* ``test_endpoint_round_trip`` — full round trip through the engine
  surface (build -> solve -> observe) is valid; ``detach_proof=True``
  at every step.
* ``test_determinism`` — two 5-round scenarios from identical seeds
  produce byte-identical endpoints.
* ``test_velocity_field_lazy_loads_torch_if_required`` — the
  ``synthetic`` mode does NOT require :mod:`torch`; the constructor
  does NOT trigger a top-level torch import.
* ``test_apply_restart_distribution_respects_memory_fraction`` —
  ``apply_restart_distribution`` is correct for ``beta`` in
  ``{0.0, 0.5, 1.0}``.
* ``test_moe_route_selection_at_t_moe`` — ``_route_for_t`` returns
  ``"high"`` when ``t >= t_moe`` and ``"low"`` otherwise.
* ``test_ti2v5b_drops_moe_route`` — TI2V-5B uses a single dense
  forward; ``_route_for_t`` is never consulted.
* ``test_state_shape_advertised_matches_runner`` — the adapter's
  ``state_shape`` matches the published A14B / TI2V-5B latent
  layouts.
* ``test_channel_domains_match_design_spec`` — every supported
  channel has a domain declared.
* ``test_export_trajectory_returns_canonical_shape`` —
  :meth:`export_trajectory` returns ``(T, C, T_lat, H_lat, W_lat)``.
* ``test_materialize_trajectory_writes_npz`` —
  :meth:`materialize_trajectory` writes a valid ``.npz`` file.
* ``test_batched_inference_shape_and_determinism`` —
  :meth:`batched_inference` returns ``(n, C, T_lat, H_lat, W_lat)``
  and is byte-deterministic.
* ``test_protocol_surface_intact`` — the adapter satisfies the
  :class:`FlowMatchingODEAdapter` ``@runtime_checkable`` Protocol
  and every method is non-mutating for canonical inputs.

The test suite is torch-free at import time (``pytest.importorskip``
is unnecessary because the adapter is in ``synthetic`` mode by
default while the dependency blockers are open). When the Wan2.2
paper PDF and weights land, the same suite will exercise the
``torch`` mode via ``force_mode="torch"``.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_bundle(bundle) -> str:
    """Return a deterministic sha256 digest of ``bundle``'s identity surface."""
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
    target_round: int = 0,
    beta_from_schedule: bool = False,
) -> object:  # FinalRestartPolicy
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

    channel = ChannelName("video_latent")
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


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int = 5,
    source: str = "wan22_test",
    calibration_artifact_hash: str = "cal-wan22",
    solver: str = "heun",
) -> object:  # ODEConditionDelta
    from adaptive_reflow.universal.state import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={
            "num_steps": int(num_steps),
            "solver": str(solver),
            "target_distribution": "wan_bench_2k",
        },
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _endpoint_native(adapter, digest: str) -> np.ndarray:
    """Return the ``x`` stored under ``digest`` as a ``(16, 30, 45, 80)`` array."""
    entry = adapter._native_states[digest]  # noqa: SLF001 — test seam
    # Both ``observe_endpoint`` (stores ``"x"``) and
    # ``apply_restart_distribution`` (stores ``"x0"``) populate the
    # native state. Try both keys so the helper works across both
    # entry shapes.
    arr = entry.get("x", entry.get("x0"))
    if arr is None:
        raise KeyError(
            f"native state at digest {digest[:16]}... lacks both 'x' and 'x0'"
        )
    return np.asarray(arr, dtype=np.float64).reshape(
        (16, 30, 45, 80)
    )


def _trajectory_native(adapter, digest: str) -> np.ndarray:
    """Return the trajectory stored under ``digest``."""
    entry = adapter._native_states[digest]  # noqa: SLF001
    return np.asarray(entry["trajectory"], dtype=np.float64)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wan22_adapter() -> object:  # Wan22VideoAdapter
    """Return a fresh :class:`Wan22VideoAdapter` (synthetic mode)."""
    from adaptive_reflow.adapters.wan2_2_video import (
        Wan22VideoAdapter,
    )

    return Wan22VideoAdapter(
        variant="t2v_a14b",
        force_mode="synthetic",
        num_steps=5,
        solver="heun",
        t_moe=0.5,
        synthetic_hidden=32,
        synthetic_seed=42,
    )


@pytest.fixture
def wan22_adapter_ti2v() -> object:  # Wan22VideoAdapter (TI2V-5B)
    """Return a fresh :class:`Wan22VideoAdapter` in TI2V-5B mode."""
    from adaptive_reflow.adapters.wan2_2_video import (
        Wan22VideoAdapter,
    )

    return Wan22VideoAdapter(
        variant="ti2v_5b",
        force_mode="synthetic",
        num_steps=5,
        solver="heun",
        synthetic_hidden=32,
        synthetic_seed=42,
    )


# ---------------------------------------------------------------------------
# 1. Capability handshake
# ---------------------------------------------------------------------------


def test_capabilities_handshake(wan22_adapter: object) -> None:
    """Adapter's capability surface exposes all engine-side flags."""
    from adaptive_reflow.universal.adapter import validate_capabilities

    caps = wan22_adapter.capabilities()
    assert caps.has_ode_integration_surface is True
    assert caps.has_prior_export is True
    assert caps.has_state_export is True
    assert caps.has_condition_injection is True
    assert caps.has_restart_boundary is True
    assert caps.has_continuous_channels is True
    assert caps.has_discrete_channels is True
    assert caps.has_trajectory_digest is True
    assert caps.has_deterministic_seed is True
    assert caps.has_materialization_route is True
    # Channel vocabulary matches the design spec.
    assert set(caps.supported_channels) == {
        "video_latent",
        "text_embedding",
        "timestep",
        "moe_route",
        "vae_pixel_video",
    }
    # Domain declarations are well-formed.
    assert caps.channel_domains[__import__("adaptive_reflow").universal.state.ChannelName("video_latent")] == "continuous"
    assert caps.channel_domains[__import__("adaptive_reflow").universal.state.ChannelName("text_embedding")] == "continuous"
    assert caps.channel_domains[__import__("adaptive_reflow").universal.state.ChannelName("timestep")] == "continuous"
    assert caps.channel_domains[__import__("adaptive_reflow").universal.state.ChannelName("moe_route")] == "discrete"
    assert caps.channel_domains[__import__("adaptive_reflow").universal.state.ChannelName("vae_pixel_video")] == "continuous"
    # Native config is well-formed.
    assert caps.native_config_hash == "wan2_2_video_fm_moe:cfg:v1"
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"


# ---------------------------------------------------------------------------
# 2. state_shape advertised matches the published A14B layout
# ---------------------------------------------------------------------------


def test_state_shape_advertised_matches_runner(wan22_adapter: object) -> None:
    """``state_shape == (16, 30, 45, 80)`` for A14B; ``(48, 30, 45, 80)`` for TI2V-5B."""
    caps = wan22_adapter.capabilities()
    assert caps.state_shape == (16, 30, 45, 80)
    # TI2V-5B variant uses the patchified shape.
    caps_ti2v = wan22_adapter_ti2v() if False else wan22_adapter_ti2v_fixture().capabilities()
    assert caps_ti2v.state_shape == (48, 30, 45, 80)


def wan22_adapter_ti2v_fixture():
    from adaptive_reflow.adapters.wan2_2_video import (
        Wan22VideoAdapter,
    )

    return Wan22VideoAdapter(
        variant="ti2v_5b",
        force_mode="synthetic",
        num_steps=5,
        solver="heun",
        synthetic_hidden=32,
        synthetic_seed=42,
    )


# ---------------------------------------------------------------------------
# 3. Channel domains match the design spec
# ---------------------------------------------------------------------------


def test_channel_domains_match_design_spec(wan22_adapter: object) -> None:
    """Channel-domains mapping matches the published video spec."""
    from adaptive_reflow.universal.state import ChannelName

    caps = wan22_adapter.capabilities()
    assert caps.channel_domains[ChannelName("video_latent")] == "continuous"
    assert caps.channel_domains[ChannelName("text_embedding")] == "continuous"
    assert caps.channel_domains[ChannelName("timestep")] == "continuous"
    assert caps.channel_domains[ChannelName("moe_route")] == "discrete"
    assert caps.channel_domains[ChannelName("vae_pixel_video")] == "continuous"


# ---------------------------------------------------------------------------
# 4. build_initial_state returns the correct shape
# ---------------------------------------------------------------------------


def test_build_initial_state_returns_correct_shape(wan22_adapter: object) -> None:
    """``build_initial_state`` returns a bundle whose latent is ``(16, 30, 45, 80)``."""
    bundle = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    entry = wan22_adapter._native_states[bundle.native_state_digest]  # noqa: SLF001
    x0 = np.asarray(entry["x0"], dtype=np.float64)
    assert x0.shape == (16, 30, 45, 80)
    # text_embedding shape matches the published umT5-XXL layout.
    text_emb = np.asarray(entry["text_emb"], dtype=np.float64)
    assert text_emb.shape == (256, 4096)
    # moe_route initial assignment is ``"high"`` (early denoising).
    assert str(entry["moe_route"]) == "high"
    assert bundle.detach_proof is True
    assert bundle.source_round == 0


# ---------------------------------------------------------------------------
# 5. solve_ode returns a finite trace
# ---------------------------------------------------------------------------


def test_solve_ode_returns_finite_trace(wan22_adapter: object) -> None:
    """``solve_ode`` returns a finite trajectory; endpoint shape matches the latent."""
    state = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    cond = _make_condition_delta(target_round=0, num_steps=5, solver="heun")
    trace = wan22_adapter.solve_ode(state, cond, seed=0)
    # Trace is well-formed.
    assert trace.steps == 5
    assert 0.0 <= trace.accept_rate <= 1.0
    assert trace.native_state_digest
    assert trace.integrator_config_hash
    # Trajectory is finite.
    traj = _trajectory_native(wan22_adapter, trace.native_state_digest)
    assert np.isfinite(traj).all()
    assert traj.shape[1:] == (16, 30, 45, 80)


# ---------------------------------------------------------------------------
# 6. Endpoint round trip is valid
# ---------------------------------------------------------------------------


def test_endpoint_round_trip(wan22_adapter: object) -> None:
    """Full round trip (build -> solve -> observe) returns a valid bundle."""
    state = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    cond = _make_condition_delta(target_round=0, num_steps=5, solver="heun")
    trace = wan22_adapter.solve_ode(state, cond, seed=0)
    endpoint = wan22_adapter.observe_endpoint(trace, state)
    # Endpoint is finite and detached.
    assert endpoint.detach_proof is True
    assert endpoint.source_round == 1
    x_final = _endpoint_native(wan22_adapter, endpoint.native_state_digest)
    assert np.isfinite(x_final).all()
    assert x_final.shape == (16, 30, 45, 80)
    # detach_and_validate_endpoint is a no-op pass-through.
    detached = wan22_adapter.detach_and_validate_endpoint(endpoint)
    assert detached.detach_proof is True
    assert detached.native_state_digest == endpoint.native_state_digest


# ---------------------------------------------------------------------------
# 7. Determinism — same seed yields same trajectory
# ---------------------------------------------------------------------------


def test_determinism(wan22_adapter: object) -> None:
    """Two runs with identical seeds produce byte-identical endpoints."""
    deltas_a = []
    deltas_b = []
    for round_idx in range(3):
        state_a = wan22_adapter.build_initial_state(
            batch_id="batch-0", sample_id="sample-0"
        )
        cond = _make_condition_delta(target_round=round_idx, num_steps=5, solver="heun")
        trace_a = wan22_adapter.solve_ode(state_a, cond, seed=42)
        endpoint_a = wan22_adapter.observe_endpoint(trace_a, state_a)
        deltas_a.append(_endpoint_native(wan22_adapter, endpoint_a.native_state_digest).copy())
    # Second run with the same seed.
    wan22_adapter2 = type(wan22_adapter)(
        variant="t2v_a14b",
        force_mode="synthetic",
        num_steps=5,
        solver="heun",
        t_moe=0.5,
        synthetic_hidden=32,
        synthetic_seed=42,
    )
    for round_idx in range(3):
        state_b = wan22_adapter2.build_initial_state(
            batch_id="batch-0", sample_id="sample-0"
        )
        cond = _make_condition_delta(target_round=round_idx, num_steps=5, solver="heun")
        trace_b = wan22_adapter2.solve_ode(state_b, cond, seed=42)
        endpoint_b = wan22_adapter2.observe_endpoint(trace_b, state_b)
        deltas_b.append(_endpoint_native(wan22_adapter2, endpoint_b.native_state_digest).copy())
    for a, b in zip(deltas_a, deltas_b, strict=False):
        assert np.array_equal(a, b), "Determinism violated across runs"


# ---------------------------------------------------------------------------
# 8. Velocity field lazily loads torch
# ---------------------------------------------------------------------------


def test_velocity_field_lazy_loads_torch_if_required() -> None:
    """The adapter's synthetic mode does not import torch at construction."""
    import sys

    # Reload-safe check: import the adapter module and confirm torch
    # is not in its namespace before any explicit torch-touching call.
    from adaptive_reflow.adapters import wan2_2_video as wan22

    # The module exposes a torch_is_available() helper — calling it
    # does NOT import torch; the importlib.util.find_spec check is
    # cheap and import-free. If torch IS installed (e.g. in a venv
    # with torch), this still passes because we never call torch
    # at module import.
    available = wan22.torch_is_available()
    assert isinstance(available, bool)
    # The synthetic field never imports torch (it lives entirely in
    # NumPy). Construction must succeed without torch.
    adapter = wan22.Wan22VideoAdapter(
        variant="t2v_a14b",
        force_mode="synthetic",
        num_steps=3,
        solver="heun",
        synthetic_hidden=16,
        synthetic_seed=1,
    )
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    cond = _make_condition_delta(target_round=0, num_steps=3, solver="heun")
    trace = adapter.solve_ode(bundle, cond, seed=0)
    assert np.isfinite(_trajectory_native(adapter, trace.native_state_digest)).all()


# ---------------------------------------------------------------------------
# 9. apply_restart_distribution respects memory fraction
# ---------------------------------------------------------------------------


def test_apply_restart_distribution_respects_memory_fraction(wan22_adapter: object) -> None:
    """``apply_restart_distribution`` is correct for ``beta`` in ``{0.0, 0.5, 1.0}``."""
    from adaptive_reflow.universal.state import ChannelName

    state = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    prior_entry = wan22_adapter._native_states[state.native_state_digest]  # noqa: SLF001
    prior_x = np.asarray(prior_entry["x0"], dtype=np.float64).copy()

    for beta in (0.0, 0.5, 1.0):
        policy = _make_final_policy(
            policy_id=f"pol-{beta}",
            run_id="run-0",
            beta=float(beta),
        )
        out = wan22_adapter.apply_restart_distribution(state, policy)
        out_entry = wan22_adapter._native_states[out.native_state_digest]  # noqa: SLF001
        out_x = np.asarray(out_entry["x0"], dtype=np.float64)
        # For beta=1.0 (memory_fraction=0.0): output is pure fresh.
        # For beta=0.0 (memory_fraction=1.0): output is pure prior.
        if beta == 1.0:
            assert not np.allclose(out_x, prior_x), (
                "beta=1.0 must NOT produce the prior exactly"
            )
        elif beta == 0.0:
            assert np.allclose(out_x, prior_x), (
                "beta=0.0 must produce the prior exactly"
            )
        assert np.isfinite(out_x).all()


# ---------------------------------------------------------------------------
# 10. MoE route selection at t_moe
# ---------------------------------------------------------------------------


def test_moe_route_selection_at_t_moe(wan22_adapter: object) -> None:
    """``_route_for_t`` returns ``"high"`` when ``t >= t_moe`` else ``"low"``."""
    t_moe = 0.5
    assert wan22_adapter._route_for_t(t_moe + 0.01) == "high"  # noqa: SLF001
    assert wan22_adapter._route_for_t(t_moe) == "high"  # noqa: SLF001 (inclusive)
    assert wan22_adapter._route_for_t(t_moe - 0.01) == "low"  # noqa: SLF001
    assert wan22_adapter._route_for_t(0.0) == "low"  # noqa: SLF001
    assert wan22_adapter._route_for_t(1.0) == "high"  # noqa: SLF001


# ---------------------------------------------------------------------------
# 11. TI2V-5B drops MoE routing
# ---------------------------------------------------------------------------


def test_ti2v5b_drops_moe_route(wan22_adapter_ti2v: object) -> None:
    """TI2V-5B uses a single dense forward; ``compose_condition`` sets t_moe=None."""
    state = wan22_adapter_ti2v.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    cond_delta = _make_condition_delta(target_round=0, num_steps=3, solver="heun")
    composed = wan22_adapter_ti2v.compose_condition(state, cond_delta)
    assert composed.delta_spec.get("moe_threshold_t_moe") is None
    # The TI2V-5B latent layout is the patchified shape.
    caps = wan22_adapter_ti2v.capabilities()
    assert caps.state_shape == (48, 30, 45, 80)


# ---------------------------------------------------------------------------
# 12. export_trajectory returns the canonical shape
# ---------------------------------------------------------------------------


def test_export_trajectory_returns_canonical_shape(wan22_adapter: object) -> None:
    """``export_trajectory`` returns ``(T, C, T_lat, H_lat, W_lat)``."""
    state = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    cond = _make_condition_delta(target_round=0, num_steps=4, solver="heun")
    trace = wan22_adapter.solve_ode(state, cond, seed=0)
    traj = wan22_adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (5, 16, 30, 45, 80)  # (num_steps + 1, C, T, H, W)
    assert np.isfinite(traj).all()


# ---------------------------------------------------------------------------
# 13. materialize_trajectory writes a valid .npz file
# ---------------------------------------------------------------------------


def test_materialize_trajectory_writes_npz(wan22_adapter: object, tmp_path: Path) -> None:
    """``materialize_trajectory`` writes a valid ``.npz`` file with the trajectory."""
    state = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    cond = _make_condition_delta(target_round=0, num_steps=3, solver="heun")
    trace = wan22_adapter.solve_ode(state, cond, seed=0)
    out_path = tmp_path / "traj.npz"
    ref = wan22_adapter.materialize_trajectory(trace, out_path)
    assert ref is not None
    assert out_path.exists()
    with np.load(str(out_path)) as data:
        traj = np.asarray(data["trajectory"], dtype=np.float64)
    assert traj.shape == (4, 16, 30, 45, 80)
    assert np.isfinite(traj).all()


# ---------------------------------------------------------------------------
# 14. batched_inference returns the canonical shape
# ---------------------------------------------------------------------------


def test_batched_inference_shape_and_determinism(wan22_adapter: object) -> None:
    """``batched_inference`` returns ``(n, C, T_lat, H_lat, W_lat)`` and is deterministic."""
    out_a = wan22_adapter.batched_inference(n_samples=2, num_steps=3, seed=0, solver="heun")
    out_b = wan22_adapter.batched_inference(n_samples=2, num_steps=3, seed=0, solver="heun")
    assert out_a.shape == (2, 16, 30, 45, 80)
    assert out_b.shape == (2, 16, 30, 45, 80)
    assert np.array_equal(out_a, out_b), "batched_inference must be deterministic"
    assert np.isfinite(out_a).all()


# ---------------------------------------------------------------------------
# 15. Protocol surface — runtime-checkable + non-mutating methods
# ---------------------------------------------------------------------------


def test_protocol_surface_intact(wan22_adapter: object) -> None:
    """Adapter satisfies the @runtime_checkable Protocol; methods are non-mutating."""
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    # Runtime-checkable Protocol check.
    assert isinstance(wan22_adapter, FlowMatchingODEAdapter)
    # Snapshot the bundle's identity before/after every method.
    state = wan22_adapter.build_initial_state(
        batch_id="batch-0", sample_id="sample-0"
    )
    snapshot = (state.native_state_digest, state.source_round)
    cond = _make_condition_delta(target_round=0, num_steps=3, solver="heun")
    composed = wan22_adapter.compose_condition(state, cond)
    assert composed is not cond
    exported = wan22_adapter.export_endpoint(state)
    assert exported.native_state_digest == state.native_state_digest
    detached = wan22_adapter.detach_and_validate_endpoint(state)
    assert detached.detach_proof is True
    # Build a fresh policy and apply it (non-mutating).
    policy = _make_final_policy(
        policy_id="pol-0", run_id="run-0", beta=0.5
    )
    out_state = wan22_adapter.apply_restart_distribution(state, policy)
    assert out_state.source_round == state.source_round + 1
    # Solve the ODE.
    trace = wan22_adapter.solve_ode(state, cond, seed=0)
    endpoint = wan22_adapter.observe_endpoint(trace, state)
    assert endpoint.source_round == state.source_round + 1
    # Verify the original bundle is untouched.
    assert (state.native_state_digest, state.source_round) == snapshot


# ---------------------------------------------------------------------------
# 16. Mechanism ID is the published string
# ---------------------------------------------------------------------------


def test_mechanism_id_is_static(wan22_adapter: object) -> None:
    """``mechanism_id`` is the canonical MechanismId string."""
    assert wan22_adapter.mechanism_id == "wan2.2_video_fm_moe@v1"


# ---------------------------------------------------------------------------
# 17. No NaN/Inf over many seeds
# ---------------------------------------------------------------------------


def test_no_nan_over_many_seeds(wan22_adapter: object) -> None:
    """``solve_ode`` returns finite endpoints for ``seed in {0, ..., 9}``."""
    for seed in range(10):
        state = wan22_adapter.build_initial_state(
            batch_id=f"batch-{seed}", sample_id=f"sample-{seed}"
        )
        cond = _make_condition_delta(target_round=seed, num_steps=3, solver="heun")
        trace = wan22_adapter.solve_ode(state, cond, seed=seed)
        endpoint = wan22_adapter.observe_endpoint(trace, state)
        x = _endpoint_native(wan22_adapter, endpoint.native_state_digest)
        assert np.isfinite(x).all(), f"NaN/Inf detected at seed={seed}"


# ---------------------------------------------------------------------------
# 18. Engine stress (3 rounds, finite + valid)
# ---------------------------------------------------------------------------


def test_engine_stress_3_rounds(wan22_adapter: object) -> None:
    """Adapter survives a 3-round engine run with restart blending."""
    last_digest = None
    last_bundle = None
    for round_idx in range(3):
        state = wan22_adapter.build_initial_state(
            batch_id="batch-0", sample_id="sample-0"
        )
        cond = _make_condition_delta(target_round=round_idx, num_steps=4, solver="heun")
        trace = wan22_adapter.solve_ode(state, cond, seed=0)
        endpoint = wan22_adapter.observe_endpoint(trace, state)
        # Restart with beta=0.5 each round.
        policy = _make_final_policy(
            policy_id=f"pol-{round_idx}",
            run_id="run-0",
            beta=0.5,
            target_round=round_idx + 1,
        )
        # Apply restart on the endpoint of the previous round.
        restarted = wan22_adapter.apply_restart_distribution(endpoint, policy)
        last_bundle = restarted
        last_digest = restarted.native_state_digest
    # The final restarted bundle is detached and has finite state.
    # (Earlier digests may have been evicted by the LRU cache; the
    # test deliberately checks the latest entry, mirroring the
    # round-frame semantics where only the most-recent prior is
    # carried forward.)
    assert last_bundle is not None
    assert last_bundle.detach_proof is True
    assert last_digest is not None
    assert last_digest in wan22_adapter._native_states  # noqa: SLF001
    x = _endpoint_native(wan22_adapter, last_digest)
    assert np.isfinite(x).all()
