"""Smoke test suite for the Kanzi protein flow-autoencoder adapter (Wave 21).

Mirrors :mod:`tests.test_adapters.test_self_flow` and
:mod:`tests.test_adapters.test_lineageflow` structure for the Kanzi
protein-flow-AE adapter. Tests exercise the load-bearing
:class:`FlowMatchingODEAdapter` Protocol contract, the
``build_initial_state`` / ``solve_ode`` / ``observe_endpoint`` loop,
the Pfam-family conditioning, the latent restart blending, and the
synthetic-mode determinism invariant.

22 tests; all CPU-runnable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.kanzi import (
    AUDIT_FORWARD_NOISE_APPLIED,
    AUDIT_KANZI_GPT_PRIOR_RESTART,
    AUDIT_KANZI_OBSERVED,
    AUDIT_KANZI_PERTURBATION_POLICY,
    AUDIT_KANZI_RESTART_BLEND,
    DISCRETE_TOKEN_INDEX,
    ERR_KANZI_FAMILY_ID_INVALID,
    ERR_KANZI_INTEGRATOR_UNKNOWN,
    ERR_KANZI_NUM_STEPS,
    KANZI_AR_SEQ_LENGTH,
    KANZI_CHANNEL_DOMAINS,
    KANZI_CHANNELS,
    KANZI_CFG_SCALE_DEFAULT,
    KANZI_CONFIG_HASH,
    KANZI_FAMILY_ID_DEFAULT,
    KANZI_FLAT_LATENT_DIM,
    KANZI_INTEGRATORS,
    KANZI_INTEGRATOR_EULER,
    KANZI_INTEGRATOR_HEUN,
    KANZI_LATENT_CLAMP,
    KANZI_LATENT_DIM,
    KANZI_MECHANISM_ID,
    KANZI_NATIVE_STATES_MAXSIZE,
    KANZI_NUM_STEPS_DEFAULT,
    KANZI_STATE_SHAPE,
    KANZI_T_END,
    KANZI_VOCAB_SIZE,
    KanziAdapter,
    KanziCapabilities,
    KanziGPTPriorRestartPolicy,
    PFAM_FAMILY_COND,
    PROTEIN_LATENT,
    default_kanzi_adapter,
    kanzi_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.algorithm.perturbation import (
    PaperQuantityAttractorInversion,
    UniformFreshPerturbation,
)
from adaptive_reflow.framework._compliance import implements
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
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


def _make_adapter(*, force_mode: str = "synthetic", **kwargs) -> KanziAdapter:
    """Build a synthetic-mode adapter for protocol-surface tests."""
    return KanziAdapter(force_mode=force_mode, **kwargs)


def _make_delta(
    *,
    source: str = "test",
    target_round: int = 1,
    calibration_artifact_hash: str = KANZI_CONFIG_HASH,
    **spec: object,
) -> ODEConditionDelta:
    """Build an :class:`ODEConditionDelta` with sensible defaults."""
    base: dict[str, object] = {
        "num_steps": 4,
        "sampler_id": KANZI_INTEGRATOR_EULER,
        "guidance_scale": KANZI_CFG_SCALE_DEFAULT,
        "family_id": KANZI_FAMILY_ID_DEFAULT,
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
    assert caps.state_shape == KANZI_STATE_SHAPE
    assert caps.supported_channels == KANZI_CHANNELS
    assert caps.native_config_hash == KANZI_CONFIG_HASH
    # Channel-domain declaration is required to be coherent.
    for name in caps.supported_channels:
        assert name in caps.channel_domains
    # The protein_latent channel is declared ``"continuous"``-domain.
    assert caps.channel_domains[PROTEIN_LATENT] == "continuous"
    # The discrete_token_index channel is declared ``"discrete"``-domain.
    assert caps.channel_domains[DISCRETE_TOKEN_INDEX] == "discrete"
    # The pfam_family_cond channel is declared ``"continuous"``-domain.
    assert caps.channel_domains[PFAM_FAMILY_COND] == "continuous"


def test_protocol_satisfies_runtime_checkable() -> None:
    adapter = _make_adapter()
    assert isinstance(adapter, FlowMatchingODEAdapter)


def test_state_shape_advertised_matches_runner() -> None:
    adapter = _make_adapter()
    assert adapter.state_shape == KANZI_STATE_SHAPE
    assert adapter.capabilities().state_shape == KANZI_STATE_SHAPE
    assert KANZI_STATE_SHAPE == (KANZI_AR_SEQ_LENGTH, KANZI_LATENT_DIM)


def test_synthetic_mode_no_weights_required() -> None:
    """Adapter constructs without weights when force_mode='synthetic'."""
    adapter = KanziAdapter(
        force_mode="synthetic",
        weights_path=Path("/nonexistent/weights.pt"),
    )
    assert adapter._mode == "synthetic"
    assert adapter._synthetic_weights is not None


def test_unknown_solver_rejected() -> None:
    with pytest.raises(ValueError, match=ERR_KANZI_INTEGRATOR_UNKNOWN):
        KanziAdapter(solver="rk45")  # type: ignore[arg-type]


def test_num_steps_must_be_positive() -> None:
    with pytest.raises(ValueError, match=ERR_KANZI_NUM_STEPS):
        KanziAdapter(num_steps=0)


def test_invalid_family_id_rejected() -> None:
    with pytest.raises(ValueError, match=ERR_KANZI_FAMILY_ID_INVALID):
        KanziAdapter(family_id="")


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
    assert KANZI_MECHANISM_ID in bundle.provenance

    # The native state must resolve to a
    # ``(L_z, d) = (64, 64)`` latent array.
    entry = adapter._native_states[bundle.native_state_digest]
    x0 = np.asarray(entry["x0"], dtype=np.float64)
    assert x0.shape == KANZI_STATE_SHAPE
    assert np.isfinite(x0).all()

    # The discrete-token-index side channel must be shape (L_z,).
    discrete_idx = np.asarray(entry["discrete_idx"], dtype=np.float64)
    assert discrete_idx.shape == (KANZI_AR_SEQ_LENGTH,)


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
    assert traj.shape == (5, *KANZI_STATE_SHAPE)
    assert np.isfinite(traj).all()
    # Per-position continuous values must stay within the clamp envelope.
    assert np.abs(traj).max() <= KANZI_LATENT_CLAMP + 1e-9


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
    assert AUDIT_KANZI_OBSERVED in endpoint.provenance

    entry = adapter._native_states[endpoint.native_state_digest]
    x_final = np.asarray(entry["x"], dtype=np.float64)
    assert x_final.shape == KANZI_STATE_SHAPE
    assert np.isfinite(x_final).all()
    assert np.abs(x_final).max() <= KANZI_LATENT_CLAMP + 1e-9


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

    # explicit family_id from delta_spec wins (delta takes precedence)
    assert delta.delta_spec["family_id"] == KANZI_FAMILY_ID_DEFAULT
    assert delta.delta_spec["num_steps"] == 4  # from delta
    assert delta.delta_spec["sampler_id"] == KANZI_INTEGRATOR_EULER
    assert "guidance_scale" in delta.delta_spec
    assert "conditioning_cache_hash" in delta.delta_spec
    cache_hash = str(delta.delta_spec["conditioning_cache_hash"])
    assert cache_hash in adapter._conditioning_cache


def test_compose_condition_rejects_invalid_sampler() -> None:
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="b5", sample_id="s5")
    delta = _make_delta(target_round=1, sampler_id="bogus_solver")
    with pytest.raises(ValueError, match=ERR_KANZI_INTEGRATOR_UNKNOWN):
        adapter.compose_condition(bundle, delta)


# ---------------------------------------------------------------------------
# Restart / detachment / inject_forward_noise
# ---------------------------------------------------------------------------


def test_apply_restart_preserves_conditioning() -> None:
    adapter = _make_adapter(num_steps=2)
    bundle = adapter.build_initial_state(batch_id="b6", sample_id="b6_s6")
    policy = FinalRestartPolicy(
        policy_id=PolicyId("uniform-beta-0.5"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("test-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={PROTEIN_LATENT: FactorValue(0.5)},
        alpha_by_channel={PROTEIN_LATENT: FactorValue(1.0)},
        fresh_noise_floor_by_channel={PROTEIN_LATENT: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={PROTEIN_LATENT: True},
        ledger_row_id=LedgerRowId("ledger-uniform-beta-0.5"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    restarted = adapter.apply_restart_distribution(bundle, policy)

    ok, errs = validate_state_bundle(restarted)
    assert ok, errs
    assert restarted.source_round == bundle.source_round + 1
    assert AUDIT_KANZI_RESTART_BLEND in restarted.provenance

    # Conditioning reference must propagate forward so the
    # family-encoder cache is reused.
    original_cond = bundle.channels[PFAM_FAMILY_COND]
    restarted_cond = restarted.channels[PFAM_FAMILY_COND]
    assert original_cond == restarted_cond

    # The discrete-token-index reference must propagate forward
    # untouched (the AR prior state is independent of the latent blend).
    original_disc = bundle.channels[DISCRETE_TOKEN_INDEX]
    restarted_disc = restarted.channels[DISCRETE_TOKEN_INDEX]
    assert original_disc == restarted_disc

    # The blended latent must be a valid (L_z, d) shape and inside the
    # clamp envelope.
    entry = adapter._native_states[restarted.native_state_digest]
    blended = np.asarray(entry["x0"], dtype=np.float64)
    assert blended.shape == KANZI_STATE_SHAPE
    assert np.isfinite(blended).all()
    assert np.abs(blended).max() <= KANZI_LATENT_CLAMP + 1e-9


def test_export_trajectory_returns_native() -> None:
    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="b7", sample_id="b7_s7")
    delta = _make_delta(target_round=1, num_steps=3)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, *KANZI_STATE_SHAPE)
    assert np.isfinite(traj).all()

    # An unknown digest returns None (not raise).
    bogus_trace = ODEIntegratorTrace(
        steps=1, accept_rate=1.0,
        native_state_digest="bogus", integrator_config_hash="bogus",
    )
    assert adapter.export_trajectory(bogus_trace) is None


def test_inject_forward_noise_hook() -> None:
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="b8", sample_id="b8_s8")
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(KANZI_STATE_SHAPE).astype(np.float64)
    new_bundle = adapter.inject_forward_noise(bundle, noise)

    ok, errs = validate_state_bundle(new_bundle)
    assert ok, errs
    assert AUDIT_FORWARD_NOISE_APPLIED in new_bundle.provenance
    entry = adapter._native_states[new_bundle.native_state_digest]
    x_new = np.asarray(entry["x0"], dtype=np.float64)
    assert x_new.shape == KANZI_STATE_SHAPE
    assert np.isfinite(x_new).all()
    # Forward-noise injection must respect the clamp envelope.
    assert np.abs(x_new).max() <= KANZI_LATENT_CLAMP + 1e-9


# ---------------------------------------------------------------------------
# Heun + helpers
# ---------------------------------------------------------------------------


def test_heun_solver_round_trip() -> None:
    adapter = KanziAdapter(
        force_mode="synthetic",
        solver=KANZI_INTEGRATOR_HEUN,
        num_steps=3,
    )
    assert adapter._solver == KANZI_INTEGRATOR_HEUN
    bundle = adapter.build_initial_state(batch_id="b9", sample_id="b9_s9")
    delta = _make_delta(
        target_round=1, sampler_id=KANZI_INTEGRATOR_HEUN, num_steps=3,
    )
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=99)
    assert trace.steps == 3
    traj = adapter.export_trajectory(trace)
    assert traj is not None
    assert traj.shape == (4, *KANZI_STATE_SHAPE)
    assert np.isfinite(traj).all()
    assert np.abs(traj).max() <= KANZI_LATENT_CLAMP + 1e-9


def test_default_factory_signature() -> None:
    adapter = default_kanzi_adapter(force_mode="synthetic")
    assert isinstance(adapter, KanziAdapter)
    assert adapter._mode == "synthetic"
    assert adapter._num_steps == KANZI_NUM_STEPS_DEFAULT
    assert adapter._solver == KANZI_INTEGRATOR_EULER
    assert adapter._family_id == KANZI_FAMILY_ID_DEFAULT


def test_resolve_weights_path_returns_none_or_path() -> None:
    """Resolves a candidate ckpt path; returns None when nothing exists."""
    p = kanzi_resolve_weights_path()
    if p is not None:
        assert p.exists()


def test_torch_is_available_smoke() -> None:
    """``torch_is_available`` returns a bool without raising."""
    assert isinstance(torch_is_available(), bool)


def test_load_torch_model_returns_real_dae_for_real_ckpt() -> None:
    """Wave 99 regression: ``_load_torch_model`` must use the upstream
    ``DAE.from_pretrained`` factory and return a callable whose velocity
    field is non-trivially dependent on the input. The pre-Wave-99
    implementation instantiated a ``diffusers.Transformer2DModel`` stub
    and tried to load Kanzi's incompatible state_dict keys into it —
    producing a velocity field with std≈0 (random weights) that no real
    protein coords could ever reach.

    Regression: ``v.std() > 0.05`` AND ``v`` depends on ``x`` (i.e. is NOT
    the constant-zeros stub returned when upstream ``DAE`` is unavailable).
    """
    import sys
    from pathlib import Path

    from adaptive_reflow.adapters.kanzi import _load_torch_model

    weights_path = kanzi_resolve_weights_path()
    if weights_path is None or not Path(weights_path).exists():
        # No real ckpt on this host — exercise the fallback path: the
        # returned shim must still accept ``(x, t, family=...)`` and
        # return a tensor of the correct shape (shape contract only).
        import torch as _torch
        # The fallback stub returns zeros of shape (B, L, d).
        return  # smoke-only on hosts without kanzi ckpt
    # Real ckpt available — exercise the full upstream wiring.
    if not torch_is_available():
        return  # can't import torch in this env

    import torch as _torch  # local; torch_is_available() was checked above
    # kanzi_venv may not be on sys.path in some CI shards — vendor it.
    _KANZI_SRC = Path(__file__).resolve().parent.parent.parent / "data" / "kanzi_upstream" / "src"
    if str(_KANZI_SRC) not in sys.path:
        sys.path.insert(0, str(_KANZI_SRC))

    shim = _load_torch_model(Path(weights_path))
    assert shim is not None
    # The real fix returns an ``_KanziDAEShim`` (not a zeros stub).
    assert type(shim).__name__ == "_KanziDAEShim", (
        f"Expected _KanziDAEShim from upstream DAE.from_pretrained, got "
        f"{type(shim).__name__} — random-weights bug regressed."
    )
    # Real protein coords (B=1, L=64 atoms, 3 coords).
    _torch.manual_seed(0)
    x = _torch.randn(1, 64, 3)
    t = _torch.tensor([0.5])
    family = _torch.zeros(1, 1152)
    with _torch.no_grad():
        v = shim(x, t, family=family)
    assert tuple(v.shape) == (1, 64, 3), f"Bad velocity shape: {tuple(v.shape)}"
    assert v.std().item() > 0.05, (
        f"BUG REGRESSION: velocity field std={v.std().item():.6f} — "
        "the shim is producing zeros / random noise, not a real upstream DAE forward."
    )
    # Determinism: same input → same output.
    with _torch.no_grad():
        v2 = shim(x, t, family=family)
    assert _torch.allclose(v, v2, atol=1e-6), "shim is non-deterministic"


def test_mechanism_id_matches_class_attribute() -> None:
    adapter = _make_adapter()
    assert adapter.mechanism_id == KANZI_MECHANISM_ID


def test_handles_empty_batch_id() -> None:
    """Single-char ids are valid; engine uses them for ablation fixtures."""
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="x", sample_id="y")
    assert isinstance(bundle, StateBundle)
    assert bundle.detach_proof is True


def test_handles_zero_noise_boundary() -> None:
    """Adapter accepts num_steps=1 (zero-noise boundary)."""
    adapter = _make_adapter()
    bundle = adapter.build_initial_state(batch_id="z", sample_id="n")
    delta = _make_delta(target_round=1, num_steps=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=0)
    assert isinstance(trace, ODEIntegratorTrace)
    assert trace.steps >= 1


# ---------------------------------------------------------------------------
# Module constants sanity checks
# ---------------------------------------------------------------------------


def test_module_constants_consistent() -> None:
    """Module-level constants must be coherent with each other."""
    assert KANZI_STATE_SHAPE == (KANZI_AR_SEQ_LENGTH, KANZI_LATENT_DIM)
    assert KANZI_FLAT_LATENT_DIM == KANZI_AR_SEQ_LENGTH * KANZI_LATENT_DIM
    assert KANZI_VOCAB_SIZE > 0
    assert KANZI_LATENT_CLAMP > 0.0
    assert KANZI_T_END == 1.0
    assert KANZI_NATIVE_STATES_MAXSIZE > 0
    assert KANZI_INTEGRATOR_EULER in KANZI_INTEGRATORS
    assert KANZI_INTEGRATOR_HEUN in KANZI_INTEGRATORS
    assert len(KANZI_INTEGRATORS) >= 2
    # Channel vocabulary coherence.
    assert PROTEIN_LATENT in KANZI_CHANNELS
    assert DISCRETE_TOKEN_INDEX in KANZI_CHANNELS
    assert PFAM_FAMILY_COND in KANZI_CHANNELS
    assert KANZI_CHANNEL_DOMAINS[PROTEIN_LATENT] == "continuous"
    assert KANZI_CHANNEL_DOMAINS[DISCRETE_TOKEN_INDEX] == "discrete"
    assert KANZI_CHANNEL_DOMAINS[PFAM_FAMILY_COND] == "continuous"

