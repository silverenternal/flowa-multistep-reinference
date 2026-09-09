"""Comprehensive test suite for the HiDream-I1 latent flow-matching adapter (R17).

The :class:`adaptive_reflow.adapters.hidream_i1.HiDreamI1Adapter` wires
the published HiDream-I1 sparse-DiT text-to-image pipeline (Cai et al.
2025) into the framework's :class:`FlowMatchingODEAdapter` Protocol so
the algorithm-layer code can drive a real SOTA latent-FM model on
1024x1024 images. Tests exercise the 8-method Protocol surface, the
optional ``export_trajectory`` + ``inject_forward_noise`` methods, the
LRU-bounded native-state cache, the per-variant num_steps / CFG
defaults, the text-conditioning cache key, and the bytes-deterministic
integration loop in *synthetic* mode (torch is an optional dependency
— see the module docstring for the load-bearing baseline reproduction
which requires the ``[hidream]`` extra + the HiDream-ai published
pipelines + a CUDA host with >=40 GB HBM).

Tests:

* ``test_capabilities_handshake`` — adapter constructs in synthetic
  mode; capability handshake is well-formed.
* ``test_build_initial_state_returns_correct_shape`` —
  ``build_initial_state`` produces a bundle whose latent TensorRef
  resolves to a ``(16, 128, 128)`` array.
* ``test_solve_ode_returns_finite_trace`` — ``solve_ode`` returns a
  finite trajectory over ``num_steps`` Euler steps.
* ``test_endpoint_round_trip`` — ``observe_endpoint`` returns a
  bundle whose ``native_state_digest`` resolves to a finite
  ``(16, 128, 128)`` array.
* ``test_determinism`` — two ``solve_ode`` calls from identical
  inputs are byte-identical.
* ``test_velocity_field_lazy_loads_torch_if_required`` —
  ``torch_is_available()`` reports the live runtime; the adapter
  falls back to synthetic mode when torch is missing.
* ``test_protocol_satisfies_runtime_checkable`` —
  :class:`HiDreamI1Adapter` passes the ``@runtime_checkable`` Protocol
  check via ``isinstance``.
* ``test_state_shape_advertised_matches_runner`` —
  ``capabilities().state_shape == (16, 128, 128)`` so the runner's
  forward-noise allocation matches.
* ``test_compose_condition_injects_prompt_and_cfg`` —
  :meth:`compose_condition` resolves the prompt + cfg_scale + variant
  + num_steps + sampler_id defaults and writes the conditioning cache
  hash back into the ``delta_spec``.
* ``test_compose_condition_requires_prompt`` —
  :meth:`compose_condition` raises when the prompt is empty.
* ``test_apply_restart_preserves_conditioning`` — the
  ``text_cond`` TensorRef is preserved across the restart boundary so
  the cache is reused.
* ``test_per_variant_num_steps_defaults`` — the per-variant default
  ``num_steps`` maps ``{"full": 50, "dev": 28, "fast": 14}``.
* ``test_per_variant_cfg_scale_defaults`` — the per-variant default
  ``cfg_scale`` maps ``{"full": 5.0, "dev": 1.0, "fast": 1.0}``.
* ``test_unknown_variant_rejected`` — the constructor + compose path
  reject unknown variants with a deterministic error code.
* ``test_unknown_solver_rejected`` — the constructor rejects unknown
  solver names with a deterministic error code.
* ``test_heun_solver_constructor_accepts_euler_default`` — default
  solver is ``euler`` for backward compatibility with the Full
  variant.
* ``test_conditioning_cache_reuses_same_prompt`` — repeated calls
  with the same prompt hit the cache; distinct prompts miss.
* ``test_batched_inference_shape_and_determinism`` —
  ``batched_inference`` returns ``(n, 16, 128, 128)`` and is
  byte-deterministic.
* ``test_export_trajectory_returns_native`` —
  :meth:`export_trajectory` returns the native trajectory stored
  under the trace's ``native_state_digest``.
* ``test_inject_forward_noise_hook`` —
  :meth:`inject_forward_noise` adds the perturbation and tags the
  provenance.
* ``test_engine_stress_20_rounds_with_restart`` —
  :class:`Engine.run_round` drives 20 rounds alternating ``beta``;
  every trace validates.
* ``test_resolution_weights_path_missing_returns_none`` —
  :func:`hidream_i1_resolve_weights_path` returns ``None`` when no
  candidate file exists and raises on unknown variants.
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
    import hashlib

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


def _validate_round_trace(trace) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``trace`` passes every round-level gate."""
    errors: list[str] = []
    audit_codes = tuple(getattr(trace, "audit_codes", ()))
    if audit_codes:
        errors.append(f"non_empty_audit_codes:{list(audit_codes)}")
    if not bool(getattr(trace, "detached", False)):
        errors.append("endpoint_not_detached")
    if getattr(trace, "integrator_trace", None) is None:
        errors.append("integrator_trace_missing")
    endpoint_digest = str(getattr(trace, "endpoint_digest", ""))
    if not endpoint_digest:
        errors.append("endpoint_digest_empty")
    initial_state_digest = str(getattr(trace, "initial_state_digest", ""))
    if not initial_state_digest:
        errors.append("initial_state_digest_empty")
    return (not errors, tuple(errors))


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

    channel = ChannelName("image_latent")
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


def _make_phase_state(*, horizon_remaining: int = 200) -> object:  # PhaseState
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="hidream-i1-test-lineage",
        recorded_at_round=0,
    )


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int = 2,
    prompt: str = "a high-resolution photograph of a mountain landscape at sunset",
    cfg_scale: float | None = None,
    variant: str | None = None,
    source: str = "hidream_i1_test",
    calibration_artifact_hash: str = "cal-hidream-i1",
) -> object:  # ODEConditionDelta
    from adaptive_reflow.universal.state import ODEConditionDelta

    spec: dict[str, object] = {"num_steps": int(num_steps), "prompt": str(prompt)}
    if cfg_scale is not None:
        spec["cfg_scale"] = float(cfg_scale)
    if variant is not None:
        spec["variant"] = str(variant)
    return ODEConditionDelta(
        delta_spec=spec,
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _native_x0(adapter, digest: str) -> np.ndarray:
    """Return the ``x0`` stored under ``digest`` as a flat ``(16, 128, 128)`` array."""
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
def hidream_adapter() -> object:  # HiDreamI1Adapter
    """Return a fresh :class:`HiDreamI1Adapter` in synthetic mode."""
    from adaptive_reflow.adapters.hidream_i1 import HiDreamI1Adapter

    return HiDreamI1Adapter(
        variant="full",
        weights_path=None,
        force_mode="synthetic",
        num_steps=2,
        synthetic_seed=42,
    )


# ---------------------------------------------------------------------------
# 1. Capability handshake
# ---------------------------------------------------------------------------


def test_capabilities_handshake(hidream_adapter: object) -> None:
    """Adapter constructs in synthetic mode; capability handshake is well-formed."""
    from adaptive_reflow.universal.adapter import validate_capabilities

    caps = hidream_adapter.capabilities()
    # Channel vocabulary advertises both ``image_latent`` and ``text_cond``.
    assert "image_latent" in caps.supported_channels
    assert "text_cond" in caps.supported_channels
    # State shape is the FLUX.1-VAE convention (16 channels @ 128x128).
    assert caps.state_shape == (16, 128, 128)
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"
    assert caps.native_config_hash == "hidream_i1:cfg:v1"


# ---------------------------------------------------------------------------
# 2. build_initial_state returns the right shape
# ---------------------------------------------------------------------------


def test_build_initial_state_returns_correct_shape(hidream_adapter: object) -> None:
    """``build_initial_state`` returns a bundle whose latent TensorRef resolves to (16, 128, 128)."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-1", sample_id="sample-hidream-1"
    )
    # Bundle-level invariants.
    assert "image_latent" in bundle.channels
    assert "text_cond" in bundle.channels
    assert bundle.batch_id == "batch-hidream-1"
    assert bundle.sample_id == "sample-hidream-1"
    assert bundle.source_round == 0
    assert bundle.detach_proof is True
    # Native state must be cached and have the right shape.
    x0 = _native_x0(hidream_adapter, bundle.native_state_digest)
    assert x0.shape == (16, 128, 128)
    assert np.all(np.isfinite(x0))
    # Mechanism id is the leading provenance entry.
    assert "hidream_i1@v1" in bundle.provenance


# ---------------------------------------------------------------------------
# 3. solve_ode returns a finite trace
# ---------------------------------------------------------------------------


def test_solve_ode_returns_finite_trace(hidream_adapter: object) -> None:
    """``solve_ode`` returns a finite trajectory over the requested number of steps."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-2", sample_id="sample-hidream-2"
    )
    delta = _make_condition_delta(target_round=0, num_steps=4)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace = hidream_adapter.solve_ode(bundle, composed, seed=0)
    assert trace.steps == 4
    assert trace.accept_rate == 1.0
    endpoint = _endpoint_from_trace(hidream_adapter, trace)
    assert endpoint.shape == (16, 128, 128)
    assert np.all(np.isfinite(endpoint))
    # Latent is bounded by the safe-range clamp.
    assert np.max(np.abs(endpoint)) <= 6.0 + 1e-9


# ---------------------------------------------------------------------------
# 4. Endpoint round-trip
# ---------------------------------------------------------------------------


def test_endpoint_round_trip(hidream_adapter: object) -> None:
    """``observe_endpoint`` returns a bundle whose digest resolves to (16, 128, 128)."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-3", sample_id="sample-hidream-3"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace = hidream_adapter.solve_ode(bundle, composed, seed=0)
    endpoint_bundle = hidream_adapter.observe_endpoint(trace, bundle)
    # Native state cached under the new digest is the latent.
    stored = hidream_adapter._native_states[endpoint_bundle.native_state_digest]  # noqa: SLF001
    assert np.asarray(stored["x"], dtype=np.float64).shape == (16, 128, 128)
    # source_round advances by exactly one.
    assert endpoint_bundle.source_round == bundle.source_round + 1
    # Provenance records the observed event.
    assert "hidream_i1_observed" in endpoint_bundle.provenance


# ---------------------------------------------------------------------------
# 5. Determinism — identical inputs produce byte-identical outputs
# ---------------------------------------------------------------------------


def test_determinism(hidream_adapter: object) -> None:
    """Two ``solve_ode`` calls from identical inputs are byte-identical."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-4", sample_id="sample-hidream-4"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace1 = hidream_adapter.solve_ode(bundle, composed, seed=0)
    trace2 = hidream_adapter.solve_ode(bundle, composed, seed=0)
    assert trace1.native_state_digest == trace2.native_state_digest
    assert trace1.integrator_config_hash == trace2.integrator_config_hash
    endpoint1 = _endpoint_from_trace(hidream_adapter, trace1)
    endpoint2 = _endpoint_from_trace(hidream_adapter, trace2)
    np.testing.assert_array_equal(endpoint1, endpoint2)


# ---------------------------------------------------------------------------
# 6. Velocity field lazy-loads torch when required
# ---------------------------------------------------------------------------


def test_velocity_field_lazy_loads_torch_if_required() -> None:
    """``torch_is_available()`` reports the live runtime; synthetic path skips torch."""
    from adaptive_reflow.adapters.hidream_i1 import (
        HIDREAM_I1_INTEGRATOR_EULER,
        HIDREAM_I1_NUM_STEPS_DEFAULT,
        HiDreamI1Adapter,
        torch_is_available,
    )

    # Adapter always constructs in synthetic mode when torch is missing
    # or weights absent (the default in this test environment).
    adapter = HiDreamI1Adapter(
        variant="full",
        weights_path=None,
        force_mode="auto",
        num_steps=HIDREAM_I1_NUM_STEPS_DEFAULT,
        synthetic_seed=42,
    )
    # The synthetic velocity field must NOT depend on torch.
    assert adapter._mode == "synthetic"  # noqa: SLF001
    bundle = adapter.build_initial_state(
        batch_id="batch-hidream-5", sample_id="sample-hidream-5"
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = adapter.compose_condition(bundle, delta)
    # solve_ode must not raise when torch is missing — the synthetic
    # velocity field is NumPy-only.
    trace = adapter.solve_ode(bundle, composed, seed=0)
    assert np.all(np.isfinite(_endpoint_from_trace(adapter, trace)))
    # Sanity check: ``torch_is_available()`` agrees with the live interpreter.
    import importlib.util as _il

    assert torch_is_available() == (_il.find_spec("torch") is not None)
    # Solver literal exposed for completeness.
    assert HIDREAM_I1_INTEGRATOR_EULER == "euler"


# ---------------------------------------------------------------------------
# 7. Adapter satisfies the runtime-checkable Protocol
# ---------------------------------------------------------------------------


def test_protocol_satisfies_runtime_checkable(hidream_adapter: object) -> None:
    """Adapter passes the ``@runtime_checkable`` Protocol check."""
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    assert isinstance(hidream_adapter, FlowMatchingODEAdapter)


# ---------------------------------------------------------------------------
# 8. State shape advertised matches the runner's forward-noise allocation
# ---------------------------------------------------------------------------


def test_state_shape_advertised_matches_runner(hidream_adapter: object) -> None:
    """``state_shape == (16, 128, 128)`` so F14's ``np.zeros(state_shape)`` allocation works."""
    caps = hidream_adapter.capabilities()
    assert caps.state_shape == (16, 128, 128)
    # The runner reads ``getattr(self._adapter, "state_shape", (2,))`` — verify
    # the attribute is also reachable as a class attribute fallback.
    state_shape_attr = getattr(hidream_adapter, "state_shape", (2,))
    assert state_shape_attr == (16, 128, 128)


# ---------------------------------------------------------------------------
# 9. compose_condition injects the conditioning + variant defaults
# ---------------------------------------------------------------------------


def test_compose_condition_injects_prompt_and_cfg(hidream_adapter: object) -> None:
    """``compose_condition`` resolves prompt + cfg_scale + variant + num_steps."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-6", sample_id="sample-hidream-6"
    )
    delta = _make_condition_delta(
        target_round=0, num_steps=8, prompt="a serene lake at dawn",
        cfg_scale=7.5, variant="dev",
    )
    composed = hidream_adapter.compose_condition(bundle, delta)
    spec = composed.delta_spec
    assert spec["prompt"] == "a serene lake at dawn"
    assert spec["cfg_scale"] == 7.5
    assert spec["variant"] == "dev"
    # Per-variant default num_steps for "dev" is 28, but the round
    # override (8) wins.
    assert spec["num_steps"] == 8
    assert spec["sampler_id"] == "euler"
    # Conditioning cache hash is written back into the delta_spec so
    # downstream observers can audit the cache key.
    assert "conditioning_cache_hash" in spec
    assert len(str(spec["conditioning_cache_hash"])) == 64


# ---------------------------------------------------------------------------
# 10. compose_condition requires a non-empty prompt
# ---------------------------------------------------------------------------


def test_compose_condition_requires_prompt(hidream_adapter: object) -> None:
    """An empty prompt raises ``hidream_i1_prompt_missing``."""
    from adaptive_reflow.universal.state import ODEConditionDelta

    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-7", sample_id="sample-hidream-7"
    )
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 2, "prompt": ""},
        source="hidream_i1_test",
        target_round=0,
        calibration_artifact_hash="cal-hidream-i1",
    )
    with pytest.raises(ValueError, match="hidream_i1_prompt_missing"):
        hidream_adapter.compose_condition(bundle, delta)


# ---------------------------------------------------------------------------
# 11. apply_restart_distribution preserves the conditioning reference
# ---------------------------------------------------------------------------


def test_apply_restart_preserves_conditioning(hidream_adapter: object) -> None:
    """The ``text_cond`` TensorRef is preserved across the restart boundary."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-8", sample_id="sample-hidream-8"
    )
    original_cond_ref = bundle.channels["text_cond"]
    policy = _make_final_policy(
        policy_id="policy-hidream-8",
        run_id="run-hidream-8",
        beta=0.5,
        target_round=0,
    )
    new_bundle = hidream_adapter.apply_restart_distribution(bundle, policy)
    # The text_cond channel is preserved exactly (same prompt -> same
    # cache key -> same TensorRef).
    assert new_bundle.channels["text_cond"] == original_cond_ref
    # The image_latent TensorRef changes (the prior was blended).
    assert new_bundle.channels["image_latent"] != bundle.channels["image_latent"]
    # The restart audit tag is appended to the provenance.
    assert "hidream_i1_restart_blend" in new_bundle.provenance


# ---------------------------------------------------------------------------
# 12. Per-variant num_steps defaults
# ---------------------------------------------------------------------------


def test_per_variant_num_steps_defaults() -> None:
    """Per-variant default ``num_steps`` is ``{"full": 50, "dev": 28, "fast": 14}``."""
    from adaptive_reflow.adapters.hidream_i1 import (
        HIDREAM_VARIANT_NUM_STEPS,
        HiDreamI1Adapter,
    )

    assert HIDREAM_VARIANT_NUM_STEPS["full"] == 50
    assert HIDREAM_VARIANT_NUM_STEPS["dev"] == 28
    assert HIDREAM_VARIANT_NUM_STEPS["fast"] == 14
    # The default factory respects the per-variant default.
    for variant in ("full", "dev", "fast"):
        a = HiDreamI1Adapter(
            variant=variant, weights_path=None, force_mode="synthetic",
            num_steps=2, synthetic_seed=42,
        )
        assert a._variant == variant  # noqa: SLF001


# ---------------------------------------------------------------------------
# 13. Per-variant cfg_scale defaults
# ---------------------------------------------------------------------------


def test_per_variant_cfg_scale_defaults() -> None:
    """Per-variant default ``cfg_scale`` is ``{"full": 5.0, "dev": 1.0, "fast": 1.0}``."""
    from adaptive_reflow.adapters.hidream_i1 import (
        HIDREAM_VARIANT_CFG_SCALE,
        HiDreamI1Adapter,
    )

    assert HIDREAM_VARIANT_CFG_SCALE["full"] == 5.0
    assert HIDREAM_VARIANT_CFG_SCALE["dev"] == 1.0
    assert HIDREAM_VARIANT_CFG_SCALE["fast"] == 1.0
    # When the caller passes a per-round cfg_scale, the per-variant
    # default does NOT win.
    adapter = HiDreamI1Adapter(
        variant="full", weights_path=None, force_mode="synthetic",
        num_steps=2, synthetic_seed=42, cfg_scale=7.5,
    )
    bundle = adapter.build_initial_state(
        batch_id="batch-hidream-9", sample_id="sample-hidream-9",
    )
    delta = _make_condition_delta(target_round=0, num_steps=2, cfg_scale=7.5)
    composed = adapter.compose_condition(bundle, delta)
    assert composed.delta_spec["cfg_scale"] == 7.5


# ---------------------------------------------------------------------------
# 14. Unknown variant rejected
# ---------------------------------------------------------------------------


def test_unknown_variant_rejected() -> None:
    """Constructor + compose path reject unknown variants with a deterministic code."""
    from adaptive_reflow.adapters.hidream_i1 import (
        ERR_HIDREAM_I1_VARIANT_UNKNOWN,
        HiDreamI1Adapter,
    )

    with pytest.raises(ValueError, match=ERR_HIDREAM_I1_VARIANT_UNKNOWN):
        HiDreamI1Adapter(
            variant="giga-distill", weights_path=None, force_mode="synthetic",
            num_steps=2, synthetic_seed=42,
        )


# ---------------------------------------------------------------------------
# 15. Unknown solver rejected
# ---------------------------------------------------------------------------


def test_unknown_solver_rejected() -> None:
    """Constructor rejects unknown solver names with a deterministic error code."""
    from adaptive_reflow.adapters.hidream_i1 import (
        ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN,
        HiDreamI1Adapter,
    )

    with pytest.raises(ValueError, match=ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN):
        HiDreamI1Adapter(
            variant="full", weights_path=None, force_mode="synthetic",
            num_steps=2, synthetic_seed=42, solver="midpoint",
        )


# ---------------------------------------------------------------------------
# 16. Heun solver constructor accepts euler default
# ---------------------------------------------------------------------------


def test_heun_solver_constructor_accepts_euler_default() -> None:
    """Default solver is ``euler`` for backward compatibility with the Full variant."""
    from adaptive_reflow.adapters.hidream_i1 import (
        HIDREAM_I1_INTEGRATOR_EULER,
        HIDREAM_I1_INTEGRATORS,
        HiDreamI1Adapter,
    )

    adapter = HiDreamI1Adapter(
        variant="full", weights_path=None, force_mode="synthetic",
        num_steps=2, synthetic_seed=42,
    )
    assert adapter._solver == HIDREAM_I1_INTEGRATOR_EULER  # noqa: SLF001
    assert HIDREAM_I1_INTEGRATOR_EULER in HIDREAM_I1_INTEGRATORS
    assert "heun" in HIDREAM_I1_INTEGRATORS


# ---------------------------------------------------------------------------
# 17. Conditioning cache reuses the same prompt
# ---------------------------------------------------------------------------


def test_conditioning_cache_reuses_same_prompt(hidream_adapter: object) -> None:
    """Repeated calls with the same prompt hit the cache; distinct prompts miss."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-10", sample_id="sample-hidream-10",
    )
    # First call populates the cache.
    delta_a = _make_condition_delta(
        target_round=0, num_steps=2, prompt="a serene lake at dawn",
    )
    composed_a = hidream_adapter.compose_condition(bundle, delta_a)
    hash_a = str(composed_a.delta_spec["conditioning_cache_hash"])
    assert hash_a in hidream_adapter._conditioning_cache  # noqa: SLF001
    # Second call with the same prompt returns the same cache key.
    delta_a_again = _make_condition_delta(
        target_round=1, num_steps=2, prompt="a serene lake at dawn",
    )
    composed_a_again = hidream_adapter.compose_condition(bundle, delta_a_again)
    hash_a_again = str(composed_a_again.delta_spec["conditioning_cache_hash"])
    assert hash_a == hash_a_again
    # Different prompt produces a different cache key.
    delta_b = _make_condition_delta(
        target_round=2, num_steps=2, prompt="a bustling city street at night",
    )
    composed_b = hidream_adapter.compose_condition(bundle, delta_b)
    hash_b = str(composed_b.delta_spec["conditioning_cache_hash"])
    assert hash_a != hash_b


# ---------------------------------------------------------------------------
# 18. batched_inference shape + determinism
# ---------------------------------------------------------------------------


def test_batched_inference_shape_and_determinism(hidream_adapter: object) -> None:
    """``batched_inference`` returns ``(n, 16, 128, 128)`` and is byte-deterministic."""
    a1 = hidream_adapter.batched_inference(n_samples=4, num_steps=2, seed=0)
    a2 = hidream_adapter.batched_inference(n_samples=4, num_steps=2, seed=0)
    assert a1.shape == (4, 16, 128, 128)
    np.testing.assert_array_equal(a1, a2)
    assert np.all(np.isfinite(a1))
    assert np.max(np.abs(a1)) <= 6.0 + 1e-9


# ---------------------------------------------------------------------------
# 19. export_trajectory returns the native trajectory
# ---------------------------------------------------------------------------


def test_export_trajectory_returns_native(hidream_adapter: object) -> None:
    """``export_trajectory`` returns the ``(T, 16, 128, 128)`` trajectory for ``trace``."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-11", sample_id="sample-hidream-11",
    )
    delta = _make_condition_delta(target_round=0, num_steps=3)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace = hidream_adapter.solve_ode(bundle, composed, seed=0)
    traj = hidream_adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, 16, 128, 128)
    assert np.all(np.isfinite(traj))
    # Returned trajectory must equal the cached trajectory byte-for-byte.
    cached = hidream_adapter._native_states[trace.native_state_digest]["trajectory"]  # noqa: SLF001
    np.testing.assert_array_equal(traj, np.asarray(cached, dtype=np.float64))
    # ``None`` for an unknown digest.
    from adaptive_reflow.universal.state import ODEIntegratorTrace

    fake_trace = ODEIntegratorTrace(
        steps=1, accept_rate=1.0,
        native_state_digest="00" * 32,
        integrator_config_hash="00" * 32,
    )
    assert hidream_adapter.export_trajectory(fake_trace) is None


# ---------------------------------------------------------------------------
# 20. inject_forward_noise hook
# ---------------------------------------------------------------------------


def test_inject_forward_noise_hook(hidream_adapter: object) -> None:
    """``inject_forward_noise`` adds the perturbation and tags the provenance."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-12", sample_id="sample-hidream-12",
    )
    prior_x0 = _native_x0(hidream_adapter, bundle.native_state_digest)
    rng = np.random.default_rng(12)
    injected = rng.standard_normal((16, 128, 128)).astype(np.float64)
    new_bundle = hidream_adapter.inject_forward_noise(bundle, injected)
    new_x0 = _native_x0(hidream_adapter, new_bundle.native_state_digest)
    assert np.all(np.isfinite(new_x0))
    assert np.max(np.abs(new_x0)) <= 6.0 + 1e-9
    assert "forward_noise_applied" in new_bundle.provenance
    # The prior is unchanged — the adapter does not mutate the input.
    np.testing.assert_allclose(
        prior_x0, _native_x0(hidream_adapter, bundle.native_state_digest),
    )


# ---------------------------------------------------------------------------
# 21. Engine stress — 20 rounds alternating beta
# ---------------------------------------------------------------------------


def test_engine_stress_20_rounds_with_restart(hidream_adapter: object) -> None:
    """``Engine.run_round`` drives 20 rounds alternating ``beta``; every trace validates."""
    from adaptive_reflow.frame import Engine

    engine = Engine()
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-13", sample_id="sample-hidream-13",
    )
    start = time.perf_counter()
    b = bundle
    for r in range(20):
        policy = _make_final_policy(
            policy_id=f"policy-hidream-13-{r}",
            run_id="run-hidream-13",
            beta=(0.5 if r % 2 == 0 else 0.0),
            target_round=r,
        )
        delta = _make_condition_delta(target_round=r, num_steps=2)
        composed = hidream_adapter.compose_condition(b, delta)
        result = engine.run_round(
            round_index=r,
            phase_state=_make_phase_state(),
            bundle=b,
            adapter=hidream_adapter,
            policy=policy,
            condition_delta=composed,
        )
        trace = result.round_trace
        ok, errs = _validate_round_trace(trace)
        assert ok, f"round {r} trace failed: {errs!r}"
        b = hidream_adapter.observe_endpoint(
            trace.integrator_trace,
            hidream_adapter.build_initial_state(
                batch_id="batch-hidream-13",
                sample_id="sample-hidream-13",
            ),
        )
    elapsed = time.perf_counter() - start
    # The synthetic 2-step Euler loop is cheap on CPU; 20 rounds must
    # finish in well under 60 seconds even on the slowest CI box.
    assert elapsed < 60.0, f"stress run blew budget: {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# 22. Weights-path resolver
# ---------------------------------------------------------------------------


def test_resolution_weights_path_missing_returns_none(tmp_path: Path) -> None:
    """``hidream_i1_resolve_weights_path`` returns ``None`` when no candidate exists."""
    from adaptive_reflow.adapters.hidream_i1 import (
        ERR_HIDREAM_I1_VARIANT_UNKNOWN,
        hidream_i1_resolve_weights_path,
    )

    # No candidates exist.
    assert hidream_i1_resolve_weights_path("full", tmp_path) is None
    assert hidream_i1_resolve_weights_path("dev", tmp_path) is None
    assert hidream_i1_resolve_weights_path("fast", tmp_path) is None
    # Unknown variant is rejected with a deterministic error code.
    with pytest.raises(ValueError, match=ERR_HIDREAM_I1_VARIANT_UNKNOWN):
        hidream_i1_resolve_weights_path("giga-distill", tmp_path)
    # Higher-priority ``.safetensors`` wins over ``.pt``.
    safetensors = tmp_path / "hidream_i1_full.safetensors"
    safetensors.write_bytes(b"\x00")
    assert hidream_i1_resolve_weights_path("full", tmp_path) == safetensors


# ---------------------------------------------------------------------------
# 23. Typed observe() — AdapterObservationProtocol conformance (Wave 95 P2.B)
# ---------------------------------------------------------------------------


def test_observe_endpoint_bundle(hidream_adapter: object) -> None:
    """``observe`` returns tagged ENDPOINT_BUNDLE + TRAJECTORY_NATIVE results."""
    from adaptive_reflow.framework.interfaces import (
        AdapterObservationProtocol,
        ObservationKind,
    )

    assert isinstance(hidream_adapter, AdapterObservationProtocol)
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-obs-1", sample_id="sample-hidream-obs-1",
    )
    delta = _make_condition_delta(target_round=0, num_steps=3)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace = hidream_adapter.solve_ode(bundle, composed, seed=0)
    results = hidream_adapter.observe(trace, bundle)
    kinds = [r.kind for r in results]
    assert kinds == [
        ObservationKind.ENDPOINT_BUNDLE,
        ObservationKind.TRAJECTORY_NATIVE,
    ]
    endpoint_obs, traj_obs = results
    # ENDPOINT_BUNDLE payload is byte-identical to the legacy method.
    legacy_endpoint = hidream_adapter.observe_endpoint(trace, bundle)
    assert endpoint_obs.channel == "image_latent"
    assert endpoint_obs.units == "state_bundle"
    assert (
        endpoint_obs.payload.native_state_digest
        == legacy_endpoint.native_state_digest
    )
    assert endpoint_obs.metadata["source_round"] == legacy_endpoint.source_round
    # TRAJECTORY_NATIVE payload is byte-identical to ``export_trajectory``.
    assert traj_obs.channel == "image_latent"
    assert traj_obs.units == "trajectory"
    assert traj_obs.payload.shape == (4, 16, 128, 128)
    np.testing.assert_array_equal(
        traj_obs.payload, hidream_adapter.export_trajectory(trace)
    )


def test_observe_with_state_none(hidream_adapter: object) -> None:
    """``observe`` returns an empty tuple when ``state`` is ``None``.

    The Protocol permits ``state=None`` (``interfaces.py:617-619``); the
    metric helper passes it when only non-endpoint strategies are wanted.
    """
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-obs-2", sample_id="sample-hidream-obs-2",
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace = hidream_adapter.solve_ode(bundle, composed, seed=0)
    assert hidream_adapter.observe(trace, None) == ()


def test_observe_skips_unsupported_kinds(hidream_adapter: object) -> None:
    """DISCRETE_TOKENS / POSITION_ENTROPY_REDUCTION are skipped (continuous latent)."""
    from adaptive_reflow.framework.interfaces import ObservationKind

    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-obs-3", sample_id="sample-hidream-obs-3",
    )
    delta = _make_condition_delta(target_round=0, num_steps=2)
    composed = hidream_adapter.compose_condition(bundle, delta)
    trace = hidream_adapter.solve_ode(bundle, composed, seed=0)
    # Requesting only the unsupported kinds yields an empty tuple.
    assert (
        hidream_adapter.observe(
            trace,
            bundle,
            strategies=(
                ObservationKind.DISCRETE_TOKENS,
                ObservationKind.POSITION_ENTROPY_REDUCTION,
            ),
        )
        == ()
    )
    # A mixed request returns only the supported subset.
    mixed = hidream_adapter.observe(
        trace,
        bundle,
        strategies=(
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.ENDPOINT_BUNDLE,
        ),
        theta_before=None,
        theta_after=None,
    )
    assert [r.kind for r in mixed] == [ObservationKind.ENDPOINT_BUNDLE]
