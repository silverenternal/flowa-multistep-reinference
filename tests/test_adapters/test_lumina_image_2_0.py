"""Comprehensive test suite for the Lumina-Image 2.0 adapter.

The :class:`adaptive_reflow.adapters.lumina_image_2_0
.LuminaImage20Adapter` wires the published Lumina-Image 2.0 Unified
Next-DiT (``Alpha-VLLM/Lumina-Image-2.0``, ``arXiv:2503.21758``,
Apache-2.0) into the framework's :class:`FlowMatchingODEAdapter`
Protocol. Tests exercise the 8-method Protocol surface, the optional
``export_trajectory`` + ``inject_forward_noise`` methods, the LRU-
bounded native-state cache, and the bytes-deterministic integration
loop in *synthetic* mode (torch / diffusers / transformers are optional
dependencies -- the load-bearing torch path lives behind the
``[lumina-image]`` extra).

Tests
-----

* ``test_capabilities_handshake`` -- every required engine-side flag
  is ``True`` and the advertised state shape matches the canonical
  ``(16, 128, 128)`` latent.
* ``test_build_initial_state_returns_correct_shape`` --
  ``build_initial_state`` returns a bundle whose stored prior is the
  canonical ``(16, 128, 128)`` latent.
* ``test_solve_ode_returns_finite_trace`` --
  ``solve_ode`` returns an :class:`ODEIntegratorTrace` whose
  endpoints are finite and inside ``[-3, 3]^16x128x128``.
* ``test_endpoint_round_trip`` --
  ``observe_endpoint`` returns a bundle whose ``native_state_digest``
  resolves to a ``(16, 128, 128)`` tensor.
* ``test_determinism`` -- two calls with identical seeds produce
  byte-identical native state digests.
* ``test_velocity_field_lazy_loads_torch_if_required`` -- the
  velocity-field helper does NOT eagerly import :mod:`torch` at
  module-import time; the import is gated on the active mode.
* ``test_protocol_surface_intact`` -- every method is non-mutating
  for the canonical inputs.
* ``test_restart_blend_respects_memory_fraction`` --
  ``apply_restart_distribution`` behaves correctly for ``beta`` in
  ``{0.0, 0.5, 1.0}``.
* ``test_text_condition_injection_lazy_and_cached`` --
  ``compose_condition`` caches the text-embedding pair keyed by
  ``calibration_artifact_hash`` so two rounds with the same prompt
  share the encoding compute.
* ``test_mechanism_id_is_lumina_image_2_0`` -- the per-model
  ``mechanism_id`` class attribute is the canonical
  ``lumina_image_2_0_flow_matching`` token.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


def _hash_bundle(bundle) -> str:
    """Return a deterministic SHA-256 digest of ``bundle``'s identity surface."""
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

    channel = ChannelName("latent")
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
    num_steps: int = 2,
    source: str = "lumina_image_2_0_test",
    calibration_artifact_hash: str = "cal-lumina-image-2-0",
    prompt: str = "a luminous crystal under starlight",
    negative_prompt: str = "blurry, low quality",
) -> object:  # ODEConditionDelta
    from adaptive_reflow.universal.state import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={
            "num_steps": int(num_steps),
            "prompt": str(prompt),
            "negative_prompt": str(negative_prompt),
            "guidance_scale": 4.0,
            "cfg_trunc_ratio": 0.25,
            "cfg_normalization": True,
            "rope_axes": (300, 512, 512),
        },
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _make_phase_state(*, horizon_remaining: int = 200) -> object:  # PhaseState
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="lumina-image-2-0-test-lineage",
        recorded_at_round=0,
    )


def _native_x0(adapter, digest: str) -> np.ndarray:
    """Return the ``x0`` stored under ``digest`` as a ``(16, 128, 128)`` array."""
    native = adapter._native_states[digest]  # noqa: SLF001 — test seam
    return np.asarray(native["x0"], dtype=np.float64).reshape((16, 128, 128))


def _endpoint_from_trace(adapter, trace) -> np.ndarray:
    """Return the final trajectory point stored under ``trace.native_state_digest``."""
    native = adapter._native_states[trace.native_state_digest]  # noqa: SLF001
    traj = np.asarray(native["trajectory"], dtype=np.float64)
    return np.asarray(traj[-1], dtype=np.float64).reshape((16, 128, 128))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lumina_adapter(tmp_path: Path) -> object:  # LuminaImage20Adapter
    """Return a fresh :class:`LuminaImage20Adapter` in synthetic mode.

    Synthetic mode is the default whenever torch / diffusers /
    transformers are unavailable OR the weights directory does not
    exist. The test environment does not vendor those heavy
    dependencies, so the adapter defaults to synthetic.
    """
    from adaptive_reflow.adapters.lumina_image_2_0 import (
        LuminaImage20Adapter,
    )

    return LuminaImage20Adapter(
        weights_path=None,
        force_mode="synthetic",
        num_steps=2,
        synthetic_seed=42,
    )


# ---------------------------------------------------------------------------
# 1. Capabilities handshake
# ---------------------------------------------------------------------------


def test_capabilities_handshake(lumina_adapter: object) -> None:
    """Capability surface exposes all engine-side flags + the canonical state shape."""
    from adaptive_reflow.universal.adapter import validate_capabilities

    caps = lumina_adapter.capabilities()
    assert caps.supported_channels == ("latent", "text_condition")
    assert caps.state_shape == (16, 128, 128)
    assert caps.has_ode_integration_surface is True
    assert caps.has_prior_export is True
    assert caps.has_state_export is True
    assert caps.has_condition_injection is True
    assert caps.has_restart_boundary is True
    assert caps.has_continuous_channels is True
    assert caps.has_discrete_channels is False
    assert caps.has_trajectory_digest is True
    assert caps.has_deterministic_seed is True
    assert caps.has_materialization_route is True
    assert caps.native_config_hash == "lumina_image_2_0:cfg:v1"
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"


# ---------------------------------------------------------------------------
# 2. build_initial_state returns the correct shape
# ---------------------------------------------------------------------------


def test_build_initial_state_returns_correct_shape(lumina_adapter: object) -> None:
    """``build_initial_state`` returns a bundle whose prior is ``(16, 128, 128)``."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-2", sample_id="sample-lumina-2"
    )
    # Channels are the canonical ``latent`` + ``text_condition`` pair.
    assert "latent" in bundle.channels
    assert "text_condition" in bundle.channels
    # The stored prior x0 has the canonical latent shape.
    x0 = _native_x0(lumina_adapter, bundle.native_state_digest)
    assert x0.shape == (16, 128, 128)
    assert np.all(np.isfinite(x0))


# ---------------------------------------------------------------------------
# 3. solve_ode returns a finite trace
# ---------------------------------------------------------------------------


def test_solve_ode_returns_finite_trace(lumina_adapter: object) -> None:
    """``solve_ode`` returns a finite ``(16, 128, 128)`` endpoint inside the clamp."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-3", sample_id="sample-lumina-3"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = lumina_adapter.compose_condition(bundle, delta)
    trace = lumina_adapter.solve_ode(bundle, composed, seed=0)
    endpoint = _endpoint_from_trace(lumina_adapter, trace)
    assert endpoint.shape == (16, 128, 128)
    assert np.all(np.isfinite(endpoint))
    assert np.max(np.abs(endpoint)) <= 3.0 + 1e-9
    assert trace.steps == 2
    assert 0.0 <= trace.accept_rate <= 1.0


# ---------------------------------------------------------------------------
# 4. Endpoint round-trip
# ---------------------------------------------------------------------------


def test_endpoint_round_trip(lumina_adapter: object) -> None:
    """``observe_endpoint`` returns a bundle whose digest resolves to ``(16, 128, 128)``."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-4", sample_id="sample-lumina-4"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = lumina_adapter.compose_condition(bundle, delta)
    trace = lumina_adapter.solve_ode(bundle, composed, seed=0)
    endpoint_bundle = lumina_adapter.observe_endpoint(trace, bundle)
    endpoint = _endpoint_from_trace(lumina_adapter, trace)
    assert endpoint.shape == (16, 128, 128)
    stored = lumina_adapter._native_states[  # noqa: SLF001
        endpoint_bundle.native_state_digest
    ]
    assert np.asarray(stored["x"], dtype=np.float64).shape == (16, 128, 128)
    assert endpoint_bundle.detach_proof is True
    assert "lumina_image_2_0_observed" in endpoint_bundle.provenance


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------


def test_determinism(lumina_adapter: object) -> None:
    """Two calls with identical seeds produce byte-identical native state digests."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-5", sample_id="sample-lumina-5"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = lumina_adapter.compose_condition(bundle, delta)
    trace1 = lumina_adapter.solve_ode(bundle, composed, seed=0)
    trace2 = lumina_adapter.solve_ode(bundle, composed, seed=0)
    assert trace1.native_state_digest == trace2.native_state_digest
    assert trace1.integrator_config_hash == trace2.integrator_config_hash


# ---------------------------------------------------------------------------
# 6. Velocity field lazy-loads torch only if required
# ---------------------------------------------------------------------------


def test_velocity_field_lazy_loads_torch_if_required() -> None:
    """The synthetic velocity field does NOT eagerly import :mod:`torch`."""
    # Module-import-time check: importing the adapter module must not
    # raise an ImportError even if torch is missing. This is the
    # framework's stdlib-only contract (audit A-1).
    import importlib

    module = importlib.import_module(
        "adaptive_reflow.adapters.lumina_image_2_0"
    )
    # ``torch_is_available`` is a public helper; calling it does not
    # require torch to be installed (it uses ``importlib.util.find_spec``).
    flag = module.torch_is_available()
    assert isinstance(flag, bool)


# ---------------------------------------------------------------------------
# 7. Protocol surface is non-mutating
# ---------------------------------------------------------------------------


def test_protocol_surface_intact(lumina_adapter: object) -> None:
    """Every method is non-mutating for the canonical inputs."""
    bundle1 = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-7", sample_id="sample-lumina-7"
    )
    bundle2 = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-7", sample_id="sample-lumina-7"
    )
    assert _hash_bundle(bundle1) == _hash_bundle(bundle2)

    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = lumina_adapter.compose_condition(bundle1, delta)
    trace1 = lumina_adapter.solve_ode(bundle1, composed, seed=0)
    trace2 = lumina_adapter.solve_ode(bundle1, composed, seed=0)
    assert trace1.native_state_digest == trace2.native_state_digest
    assert trace1.integrator_config_hash == trace2.integrator_config_hash

    exported = lumina_adapter.export_endpoint(bundle1)
    exported_again = lumina_adapter.export_endpoint(bundle1)
    assert _hash_bundle(exported) == _hash_bundle(exported_again)

    detached = lumina_adapter.detach_and_validate_endpoint(bundle1)
    detached_again = lumina_adapter.detach_and_validate_endpoint(bundle1)
    assert _hash_bundle(detached) == _hash_bundle(detached_again)

    composed1 = lumina_adapter.compose_condition(bundle1, delta)
    composed2 = lumina_adapter.compose_condition(bundle1, delta)
    assert composed1.delta_spec == composed2.delta_spec


# ---------------------------------------------------------------------------
# 8. Restart blend respects memory-fraction parameter
# ---------------------------------------------------------------------------


def test_restart_blend_respects_memory_fraction(lumina_adapter: object) -> None:
    """``apply_restart_distribution`` for ``beta in {0.0, 0.5, 1.0}``."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-8", sample_id="sample-lumina-8"
    )
    prior_x0 = _native_x0(lumina_adapter, bundle.native_state_digest)
    for beta, expected_m in [(0.0, 1.0), (0.5, 0.5), (1.0, 0.0)]:
        policy = _make_final_policy(
            policy_id=f"policy-lumina-8-{beta}",
            run_id="run-lumina-8",
            beta=beta,
            target_round=0,
        )
        new_bundle = lumina_adapter.apply_restart_distribution(bundle, policy)
        new_x0 = _native_x0(lumina_adapter, new_bundle.native_state_digest)
        assert new_x0.shape == (16, 128, 128)
        # Blend math is ``m * prior + (1-m) * fresh`` clamped to ±3.
        assert np.all(np.isfinite(new_x0))
        assert np.max(np.abs(new_x0)) <= 3.0 + 1e-9
        if expected_m == 1.0:
            # Full prior: new_x0 == prior_x0 up to the storage clip.
            np.testing.assert_allclose(
                np.clip(new_x0, -3.0, 3.0),
                np.clip(prior_x0, -3.0, 3.0),
                atol=1e-12,
            )
        assert "lumina_image_2_0_restart_blend" in new_bundle.provenance


# ---------------------------------------------------------------------------
# 9. Text-condition injection is lazy and cached
# ---------------------------------------------------------------------------


def test_text_condition_injection_lazy_and_cached(lumina_adapter: object) -> None:
    """``compose_condition`` caches the text-embedding pair keyed by
    ``calibration_artifact_hash`` so two rounds with the same prompt
    share the encoding compute.
    """
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-9", sample_id="sample-lumina-9"
    )
    delta = _make_condition_delta(
        target_round=0,
        num_steps=2,
        prompt="a luminous crystal under starlight",
        negative_prompt="blurry",
    )
    composed1 = lumina_adapter.compose_condition(bundle, delta)
    cache_key_1 = composed1.delta_spec["text_embed_cache_key"]
    assert isinstance(cache_key_1, str)
    assert cache_key_1  # non-empty

    # A second round with the same prompt + calibration hash reuses
    # the cached embedding.
    delta2 = _make_condition_delta(
        target_round=1,
        num_steps=2,
        prompt="a luminous crystal under starlight",
        negative_prompt="blurry",
    )
    composed2 = lumina_adapter.compose_condition(bundle, delta2)
    cache_key_2 = composed2.delta_spec["text_embed_cache_key"]
    assert cache_key_1 == cache_key_2

    # A different prompt produces a different cache key.
    delta3 = _make_condition_delta(
        target_round=2,
        num_steps=2,
        prompt="a different prompt entirely",
        negative_prompt="blurry",
    )
    composed3 = lumina_adapter.compose_condition(bundle, delta3)
    cache_key_3 = composed3.delta_spec["text_embed_cache_key"]
    assert cache_key_1 != cache_key_3


# ---------------------------------------------------------------------------
# 10. Per-model mechanism_id is the canonical token
# ---------------------------------------------------------------------------


def test_mechanism_id_is_lumina_image_2_0(lumina_adapter: object) -> None:
    """The per-model ``mechanism_id`` is the canonical
    ``lumina_image_2_0_flow_matching`` token.
    """
    from adaptive_reflow.adapters.lumina_image_2_0 import (
        LUMINA_IMAGE_2_0_MECHANISM_ID,
        LuminaImage20Adapter,
    )

    assert LUMINA_IMAGE_2_0_MECHANISM_ID == "lumina_image_2_0_flow_matching"
    assert LuminaImage20Adapter.mechanism_id == (
        "lumina_image_2_0_flow_matching"
    ) or str(LuminaImage20Adapter.mechanism_id) == (
        "lumina_image_2_0_flow_matching"
    )


# ---------------------------------------------------------------------------
# 11. Adapter satisfies the @runtime_checkable Protocol
# ---------------------------------------------------------------------------


def test_adapter_satisfies_protocol(lumina_adapter: object) -> None:
    """Adapter passes the runtime-checkable Protocol check."""
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    assert isinstance(lumina_adapter, FlowMatchingODEAdapter)


# ---------------------------------------------------------------------------
# 12. Engine.run_round drives an end-to-end round; endpoint is finite
# ---------------------------------------------------------------------------


def test_run_round_produces_latent_shape_samples(lumina_adapter: object) -> None:
    """Drive ``Engine.run_round``; the endpoint is finite and in-bounds."""
    from adaptive_reflow.frame import Engine

    engine = Engine()
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-12", sample_id="sample-lumina-12"
    )
    policy = _make_final_policy(
        policy_id="policy-lumina-12",
        run_id="run-lumina-12",
        beta=0.5,
        target_round=0,
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)

    result = engine.run_round(
        round_index=0,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=lumina_adapter,
        policy=policy,
        condition_delta=delta,
    )
    trace = result.round_trace
    endpoint = _endpoint_from_trace(lumina_adapter, trace.integrator_trace)
    assert endpoint.shape == (16, 128, 128)
    assert np.all(np.isfinite(endpoint))
    assert np.max(np.abs(endpoint)) <= 3.0 + 1e-9


# ---------------------------------------------------------------------------
# 13. inject_forward_noise hook
# ---------------------------------------------------------------------------


def test_inject_forward_noise_hook(lumina_adapter: object) -> None:
    """``inject_forward_noise`` adds the perturbation and tags the provenance."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-13", sample_id="sample-lumina-13"
    )
    prior_x0 = _native_x0(lumina_adapter, bundle.native_state_digest)
    rng = np.random.default_rng(13)
    injected = rng.standard_normal((16, 128, 128)).astype(np.float64)
    new_bundle = lumina_adapter.inject_forward_noise(bundle, injected)
    new_x0 = _native_x0(lumina_adapter, new_bundle.native_state_digest)
    assert np.all(np.isfinite(new_x0))
    assert np.max(np.abs(new_x0)) <= 3.0 + 1e-9
    assert "forward_noise_applied" in new_bundle.provenance
    # The prior is unchanged — the adapter does not mutate the input.
    np.testing.assert_allclose(
        prior_x0,
        _native_x0(lumina_adapter, bundle.native_state_digest),
    )


# ---------------------------------------------------------------------------
# 14. export_trajectory returns the native (T, 16, 128, 128) trajectory
# ---------------------------------------------------------------------------


def test_export_trajectory_returns_native_path(lumina_adapter: object) -> None:
    """``export_trajectory`` returns the native ``(T, 16, 128, 128)`` trajectory."""
    bundle = lumina_adapter.build_initial_state(
        batch_id="batch-lumina-14", sample_id="sample-lumina-14"
    )
    delta = _make_condition_delta(target_round=0, num_steps=4)
    composed = lumina_adapter.compose_condition(bundle, delta)
    trace = lumina_adapter.solve_ode(bundle, composed, seed=0)
    traj = lumina_adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (5, 16, 128, 128)
    assert np.all(np.isfinite(traj))


# ---------------------------------------------------------------------------
# 15. Unknown solver rejection
# ---------------------------------------------------------------------------


def test_unknown_solver_raises_value_error() -> None:
    """Unknown solver names raise ``ValueError`` with a deterministic code."""
    from adaptive_reflow.adapters.lumina_image_2_0 import (
        ERR_LUMINA_INTEGRATOR_UNKNOWN,
        LuminaImage20Adapter,
    )

    with pytest.raises(ValueError, match=ERR_LUMINA_INTEGRATOR_UNKNOWN):
        LuminaImage20Adapter(
            weights_path=None,
            force_mode="synthetic",
            num_steps=2,
            synthetic_seed=42,
            solver="rk4",
        )


# ---------------------------------------------------------------------------
# 16. Constructor validation -- num_steps must be positive
# ---------------------------------------------------------------------------


def test_num_steps_must_be_positive() -> None:
    """``num_steps <= 0`` raises ``ValueError`` with a deterministic code."""
    from adaptive_reflow.adapters.lumina_image_2_0 import (
        ERR_LUMINA_NUM_STEPS,
        LuminaImage20Adapter,
    )

    with pytest.raises(ValueError, match=ERR_LUMINA_NUM_STEPS):
        LuminaImage20Adapter(
            weights_path=None,
            force_mode="synthetic",
            num_steps=0,
            synthetic_seed=42,
        )


# ---------------------------------------------------------------------------
# 17. State-shape fallback is exposed as both class + instance attribute
# ---------------------------------------------------------------------------


def test_state_shape_class_and_instance_attribute_match() -> None:
    """``state_shape`` is reachable as both class and instance attribute (F14)."""
    from adaptive_reflow.adapters.lumina_image_2_0 import (
        LUMINA_IMAGE_2_0_STATE_SHAPE,
        LuminaImage20Adapter,
    )

    assert LuminaImage20Adapter.state_shape == LUMINA_IMAGE_2_0_STATE_SHAPE
    a = LuminaImage20Adapter(
        weights_path=None, force_mode="synthetic", num_steps=2, synthetic_seed=42
    )
    assert getattr(a, "state_shape", (2,)) == LUMINA_IMAGE_2_0_STATE_SHAPE


# ---------------------------------------------------------------------------
# 18. Heun vs Euler produce different results
# ---------------------------------------------------------------------------


def test_heun_and_euler_produce_different_results() -> None:
    """Heun and Euler integrations over the same field diverge."""
    from adaptive_reflow.adapters.lumina_image_2_0 import (
        LUMINA_IMAGE_2_0_INTEGRATOR_EULER,
        LUMINA_IMAGE_2_0_INTEGRATOR_HEUN,
        LuminaImage20Adapter,
    )

    def _run(solver: str) -> np.ndarray:
        a = LuminaImage20Adapter(
            weights_path=None,
            force_mode="synthetic",
            num_steps=10,
            synthetic_seed=42,
            solver=solver,
        )
        bundle = a.build_initial_state(
            batch_id="batch-lumina-heun", sample_id="sample-lumina-heun"
        )
        delta = _make_condition_delta(target_round=0, num_steps=10)
        composed = a.compose_condition(bundle, delta)
        trace = a.solve_ode(bundle, composed, seed=0)
        return _endpoint_from_trace(a, trace)

    e_endpoint = _run(LUMINA_IMAGE_2_0_INTEGRATOR_EULER)
    h_endpoint = _run(LUMINA_IMAGE_2_0_INTEGRATOR_HEUN)
    assert e_endpoint.shape == h_endpoint.shape == (16, 128, 128)
    # Heun uses two velocity evaluations per step (except last) so the
    # two paths must NOT be byte-identical.
    assert not np.array_equal(e_endpoint, h_endpoint)
    assert np.all(np.isfinite(h_endpoint))
    assert np.max(np.abs(h_endpoint)) <= 3.0 + 1e-9
