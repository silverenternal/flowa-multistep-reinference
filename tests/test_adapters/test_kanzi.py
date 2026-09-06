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
    AUDIT_KANZI_OBSERVED,
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
    PFAM_FAMILY_COND,
    PROTEIN_LATENT,
    default_kanzi_adapter,
    kanzi_resolve_weights_path,
    torch_is_available,
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


def test_byte_stable_build_initial_state() -> None:
    """Two consecutive build_initial_state calls with identical inputs produce byte-identical digests."""
    adapter = _make_adapter()
    bundle_a = adapter.build_initial_state(batch_id="byte", sample_id="stable")
    bundle_b = adapter.build_initial_state(batch_id="byte", sample_id="stable")
    assert bundle_a.native_state_digest == bundle_b.native_state_digest


def test_byte_stable_solve_ode_round_trip() -> None:
    """Two consecutive build+solve cycles produce byte-identical integrator_config_hash."""
    adapter = _make_adapter(num_steps=3)
    bundle_a = adapter.build_initial_state(batch_id="bs", sample_id="so")
    bundle_b = adapter.build_initial_state(batch_id="bs", sample_id="so")
    delta_a = _make_delta(target_round=1)
    delta_b = _make_delta(target_round=1)
    delta_a = adapter.compose_condition(bundle_a, delta_a)
    delta_b = adapter.compose_condition(bundle_b, delta_b)
    trace_a = adapter.solve_ode(bundle_a, delta_a, seed=42)
    trace_b = adapter.solve_ode(bundle_b, delta_b, seed=42)
    assert trace_a.native_state_digest == trace_b.native_state_digest
    assert trace_a.integrator_config_hash == trace_b.integrator_config_hash


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


# ---------------------------------------------------------------------------
# GPT-prior monkey-patch (Wave 40 Agent B)
# ---------------------------------------------------------------------------
#
# These tests verify the wave-40 monkey-patch that fixes the
# upstream ``kanzi.models.GPT.forward`` signature mismatch on its
# ``TransformerBlock`` block-call. They are best-effort: when the
# upstream ``kanzi`` package is unavailable (synthetic-only mode),
# the tests short-circuit cleanly.


def test_gpt_prior_patch_idempotent_when_kanzi_present() -> None:
    """Calling ``_install_gpt_prior_patch()`` twice does not double-wrap."""
    import importlib.util as _il

    if _il.find_spec("kanzi") is None:
        pytest.skip("kanzi package not installed in this venv")

    from adaptive_reflow.adapters.kanzi import (
        _install_gpt_prior_patch,
        GPT_PRIOR_PATCH_MARKER,
    )

    # First call (idempotent against the at-import-time install).
    assert _install_gpt_prior_patch() is True
    # Second call must remain idempotent.
    assert _install_gpt_prior_patch() is True

    import kanzi.models as _km

    assert getattr(_km.GPT, GPT_PRIOR_PATCH_MARKER, False) is True


def test_gpt_prior_patch_returns_false_when_kanzi_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``kanzi`` is not importable, the patch helper is a no-op."""
    import importlib.util as _il
    from adaptive_reflow.adapters import kanzi as _kanzi_adapter

    # Override find_spec for the three modules the patch checks, so it
    # sees them as absent.
    real_find_spec = _il.find_spec

    def _fake_find_spec(name: str, *args: object, **kwargs: object):
        if name in ("kanzi", "kanzi.models", "kanzi.attention"):
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(_il, "find_spec", _fake_find_spec)
    assert _kanzi_adapter._install_gpt_prior_patch() is False


def test_gpt_prior_patch_runs_gpt_forward_end_to_end() -> None:
    """The patched ``GPT.forward`` accepts (tok_BL, tgt_BL) without TypeError.

    This regression-tests the upstream bug documented in
    ``docs/audit/wave39-kanzi-real-ckpt-forward.md`` (the
    ``block_mask`` / ``pair_bias_BLLD`` signature mismatch inside
    ``kanzi.models.GPT.forward``). The patch must let the GPT-prior
    loss branch run end-to-end on the small synthetic GPT constructed
    below; the legacy upstream raises
    ``TypeError: got multiple values for argument 'pair_bias_BLLD'``
    without the patch.
    """
    import importlib.util as _il

    if _il.find_spec("kanzi") is None:
        pytest.skip("kanzi package not installed in this venv")
    if not _il.find_spec("torch"):
        pytest.skip("torch not installed in this venv")

    import torch  # noqa: E402  — local import gated on availability.
    import kanzi.models as _km  # noqa: E402
    from adaptive_reflow.adapters.kanzi import (  # noqa: E402
        _install_gpt_prior_patch,
    )

    # Install the patch in case earlier tests unloaded kanzi.
    assert _install_gpt_prior_patch() is True

    gpt = _km.GPT(
        _km.GPTConfig(
            vocab_size=21,
            n_channels=128,
            n_layers=1,
            n_heads=8,
            dropout=0.0,
            block_size=64,
            mlp_factor=4,
            bos=0,
            eos=1,
        )
    )
    gpt.eval()
    tok_BL = torch.randint(0, 21, (1, 8))
    tgt_BL = torch.randint(0, 21, (1, 8))

    with torch.no_grad():
        logits, loss = gpt(tok_BL, tgt_BL)

    assert logits.shape == (1, 8, 21)
    # The loss must be a finite scalar (cross-entropy between logits
    # and the target indices). The exact value is not load-bearing —
    # only that the call returned a finite scalar and not the
    # upstream's TypeError.
    assert torch.isfinite(logits).all()
    assert torch.isfinite(loss).item()


def test_gpt_prior_patch_runs_dae_gpt_prior_branch() -> None:
    """``DAE.forward`` (with ``gpt_prior=True``) computes ``gpt_prior_loss``.

    Regression-tests the end-to-end path that Wave 39 worked around
    by patching ``DAE.forward`` to report ``gpt_prior_loss = 0``.
    The patch must let the real GPT-prior branch run; the loss
    returned must be a finite scalar.
    """
    import importlib.util as _il

    if _il.find_spec("kanzi") is None:
        pytest.skip("kanzi package not installed in this venv")
    if not _il.find_spec("torch"):
        pytest.skip("torch not installed in this venv")

    import torch  # noqa: E402
    import kanzi.models as _km  # noqa: E402
    from adaptive_reflow.adapters.kanzi import (  # noqa: E402
        _install_gpt_prior_patch,
    )

    # Re-installation is idempotent.
    assert _install_gpt_prior_patch() is True

    dae = _km.DAE(
        _km.DAEConfig(
            n_channels_decoder=64,
            n_channels_encoder=64,
            n_layers_encoder=1,
            n_layers_decoder=1,
            n_heads=8,
            mlp_factor=4,
            use_qknorm=False,
            gpt_prior=True,
        )
    )
    dae.eval()

    x_BLD = torch.randn(2, 16, 3)
    with torch.no_grad():
        idx_BL, loss_dict = dae(x_BLD)

    assert "gpt_prior_loss" in loss_dict
    assert "flow_loss" in loss_dict
    # Both losses must be finite scalars.
    assert torch.isfinite(loss_dict["gpt_prior_loss"]).item()
    assert torch.isfinite(loss_dict["flow_loss"]).item()
    # The legacy Wave-39 workaround forced gpt_prior_loss = 0; the
    # patched path computes a real cross-entropy loss > 0 (token
    # indices are non-trivial relative to logits).
    assert float(loss_dict["gpt_prior_loss"]) > 0.0


# ---------------------------------------------------------------------------
# MEDIUM-11 conformance gate — Wave 41 Agent A
# ---------------------------------------------------------------------------


def test_kanzi_adapter_declares_implements_decorator() -> None:
    """KanziAdapter MUST carry an ``@implements(FlowMatchingODEAdapter)`` decorator.

    MEDIUM-11 of the Wave 32 framework code review
    (``docs/audit/framework-code-review.md`` §1.13) requires every
    registered adapter to declare its Protocol surface via the
    ``@implements`` decorator so that
    :func:`assert_adapter_compliance` can walk ``__protocols__`` and
    enforce structural typing. The Wave 39 Agent B regression check
    (``commit fb652bb6``) found this decorator missing on
    :class:`KanziAdapter`; the Wave 41 Agent A fix restores it.

    The test is a trip-wire: removing the decorator drops
    ``FlowMatchingODEAdapter`` from ``KanziAdapter.__protocols__`` and
    the ``isinstance(KanziAdapter, FlowMatchingODEAdapter)`` structural
    check (the registry-level CI gate) will start failing.
    """
    # The decorator records the declared Protocol set on the class.
    declared = getattr(KanziAdapter, "__protocols__", ())
    assert FlowMatchingODEAdapter in declared, (
        f"KanziAdapter missing @implements(FlowMatchingODEAdapter); "
        f"__protocols__={declared!r}"
    )

    # ``isinstance`` structural check passes for ``@runtime_checkable``
    # Protocols — the same path ``assert_adapter_compliance`` walks.
    assert isinstance(KanziAdapter, FlowMatchingODEAdapter)


def test_kanzi_adapter_default_factory_carries_implements() -> None:
    """``default_kanzi_adapter()`` instances MUST inherit the @implements set.

    Regression guard: the decorator is on the class, so every
    instance — including those produced by the ``default_kanzi_adapter``
    factory — exposes the same ``__protocols__`` tuple.
    """
    adapter = default_kanzi_adapter()
    assert FlowMatchingODEAdapter in getattr(KanziAdapter, "__protocols__", ())
    assert isinstance(adapter, FlowMatchingODEAdapter)


def test_kanzi_adapter_passes_assert_adapter_compliance() -> None:
    """``assert_adapter_compliance(KanziAdapter)`` MUST pass.

    End-to-end check that mirrors the CI gate in
    ``tests/test_framework/test_assert_adapter_compliance.py``. The
    registry-level CI gate already covers this for every registered
    family, but a local check pins the KanziAdapter-specific contract
    so a future regression (e.g. someone removes the decorator while
    editing the class signature) surfaces immediately.
    """
    from adaptive_reflow.framework.interfaces import (
        assert_adapter_compliance,
    )

    assert_adapter_compliance(KanziAdapter)


# ---------------------------------------------------------------------------
# Wave 45 F-1 regression: src_digest chain-walk
# ---------------------------------------------------------------------------


def test_observe_token_indices_returns_stored_discrete_idx_not_random() -> None:
    """F-1 (Wave 45): ``observe_token_indices`` must return the stored AR-prior
    ``discrete_idx`` carried through the native-state chain, NOT the
    uniform-random fallback.

    Before the F-1 fix the ``solve_ode`` ``_native_states.put`` payload did
    NOT carry a ``src_digest`` key, so the chain-walk at
    ``kanzi.py:1680`` always read ``""`` and immediately fell through to
    the deterministic random fallback at ``1695-1710``. Every Kanzi
    Tier-3 metric produced since Wave 44 was therefore measuring noise in
    both arms. This test pins the contract so the bug cannot silently
    return.
    """
    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="w45_f1", sample_id="s_f1")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    # Capture the AR prior discrete_idx that the build_initial_state
    # step deposited in the cache. This is the value the chain-walk
    # MUST surface through observe_token_indices.
    prior_entry = adapter._native_states[bundle.native_state_digest]
    expected_discrete_idx = np.asarray(
        prior_entry["discrete_idx"], dtype=np.float64,
    ).copy()
    assert expected_discrete_idx.shape == (int(KANZI_AR_SEQ_LENGTH),)

    # Confirm the trajectory entry now carries ``src_digest`` so the
    # chain-walk can step back to the prior entry. This is the
    # F-1 invariant.
    traj_entry = adapter._native_states[trace.native_state_digest]
    assert "src_digest" in traj_entry, (
        "F-1 regression: solve_ode must persist src_digest in the "
        "trajectory native-state entry so the observe_token_indices "
        "chain-walk can find discrete_idx without falling back to "
        "random. See docs/audit/wave45-f1-fix.md."
    )
    assert traj_entry["src_digest"] == str(bundle.native_state_digest)

    result = adapter.observe_token_indices(trace, paper_quantities=None)

    assert str(DISCRETE_TOKEN_INDEX) in result
    observed = np.asarray(result[str(DISCRETE_TOKEN_INDEX)], dtype=np.float64)

    # Shape sanity.
    assert observed.shape == (int(KANZI_AR_SEQ_LENGTH),)
    arr_int = observed.astype(np.int64)
    assert arr_int.min() >= 0
    assert arr_int.max() < int(KANZI_VOCAB_SIZE)

    # The defining F-1 invariant: the observed indices equal the
    # stored prior — NOT the uniform-random fallback. A random draw
    # over [0, 64) for a 64-length sequence is overwhelmingly unlikely
    # (probability ~ 64^{-64} for an exact match).
    np.testing.assert_array_equal(observed, expected_discrete_idx)


def test_observe_token_indices_chain_walk_through_restart() -> None:
    """F-1 robustness: the chain-walk terminates at the latest prior
    entry that carries ``discrete_idx``, even after a restart round.

    Exercises the second F-1 invariant — adding ``src_digest`` to the
    ``apply_restart_distribution`` put payload at lines 1205-1214 —
    which keeps the chain-walk honest through multi-round inference.
    """
    adapter = _make_adapter(num_steps=2)
    bundle = adapter.build_initial_state(batch_id="w45_chain", sample_id="s_chain")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace1 = adapter.solve_ode(bundle, delta, seed=42)

    policy = FinalRestartPolicy(
        policy_id=PolicyId("uniform-beta-0.5"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("test-run-chain"),
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

    delta2 = _make_delta(target_round=2)
    delta2 = adapter.compose_condition(restarted, delta2)
    trace2 = adapter.solve_ode(restarted, delta2, seed=42)

    # Restart entry must carry src_digest (F-1 robustness at 1205).
    restart_entry = adapter._native_states[restarted.native_state_digest]
    assert "src_digest" in restart_entry
    assert restart_entry["src_digest"] == str(bundle.native_state_digest)

    # Trajectory entry from round 2 must also carry src_digest so the
    # chain-walk can step back through the restart to the original
    # prior's discrete_idx.
    traj2_entry = adapter._native_states[trace2.native_state_digest]
    assert "src_digest" in traj2_entry
    assert traj2_entry["src_digest"] == str(restarted.native_state_digest)

    # The discrete_idx carried through restart equals the original
    # prior's discrete_idx (apply_restart_distribution preserves it
    # untouched at 1183-1187). observe_token_indices must surface it.
    expected = np.asarray(
        adapter._native_states[bundle.native_state_digest]["discrete_idx"],
        dtype=np.float64,
    )
    result = adapter.observe_token_indices(trace2, paper_quantities=None)
    observed = np.asarray(result[str(DISCRETE_TOKEN_INDEX)], dtype=np.float64)
    np.testing.assert_array_equal(observed, expected)