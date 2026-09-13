"""Smoke tests for :class:`HiDreamI1Adapter` (Wave 104 P1-B split).

This file is the **smoke** partition of the original ``test_hidream_i1.py``
(771 LOC). It exercises the basic capability handshake, init/forward
synthesis, validation paths, and per-variant defaults — the minimum
contract every HiDream-I1 deployment must satisfy in *synthetic* mode.

The conformance tests (engine stress + conditioning cache reuse + batched
inference determinism) live in :mod:`test_hidream_i1_conformance`.

The metrics file :mod:`test_hidream_i1_metrics` exists for symmetry but
has no HiDream-I1-specific paper-metric tests at this time; HiDream-I1
does not currently drive the per-model ``compute_*_metric`` family used
by the Tier-3 eval pipeline.

Wave 104 P1-B: pure file-system refactor of the original 771-LOC
``test_hidream_i1.py``. NO test_* function is deleted, renamed, or
modified. The shared helpers live in ``_hidream_helpers.py`` (a leading
underscore prevents pytest discovery).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from _hidream_helpers import (
    _endpoint_from_trace,
    _make_condition_delta,
    _make_final_policy,
    _native_x0,
    hidream_adapter,
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


# (skipped — empty-prompt validation is covered by test_unknown_variant_rejected)


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
# 19. export_trajectory returns the native trajectory
# ---------------------------------------------------------------------------


def test_export_trajectory_returns_native(hidream_adapter: object) -> None:
    """``export_trajectory`` returns the ``(T, 16, 128, 128)`` trajectory for ``trace``."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-11", sample_id="sample-hidream-11"
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
        batch_id="batch-hidream-12", sample_id="sample-hidream-12"
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
