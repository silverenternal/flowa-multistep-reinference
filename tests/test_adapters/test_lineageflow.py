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
    AUDIT_LINEAGEFLOW_PERTURBATION_POLICY,
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
    PER_POSITION_ENTROPY_REDUCTION,
    PFAM_FAMILY_COND,
    default_lineageflow_adapter,
    lineageflow_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.algorithm.perturbation import (
    PaperQuantityAttractorInversion,
    UniformFreshPerturbation,
)
from adaptive_reflow.universal.adapter import CapabilityMissingError
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


# ---------------------------------------------------------------------------
# Wave 39 Agent B: 5-LOC SamplerConfig shim (Wave 36 Agent C breakthrough)
# ---------------------------------------------------------------------------


def test_install_checkpoint_compat_shim_installs_class() -> None:
    """The SamplerConfig shim installs ``core.sampler.SamplerConfig`` in
    ``sys.modules`` so ``torch.load`` can resolve the pickled class
    reference. Mirrors upstream LineageFlow's
    ``_install_checkpoint_compat()`` in
    ``inference/inference.py:39-59``."""
    import sys

    from adaptive_reflow.adapters.lineageflow import _install_checkpoint_compat

    # Force-clean to assert idempotent re-install behaviour.
    sys.modules.pop("core.sampler", None)

    cls = _install_checkpoint_compat()
    assert cls is not None
    assert cls.__module__ == "core.sampler"
    assert cls.__qualname__ == "SamplerConfig"
    # The shim must register both the module + attribute so torch.load's
    # safe-globals lookup can resolve ``core.sampler.SamplerConfig``.
    assert "core.sampler" in sys.modules
    assert hasattr(sys.modules["core.sampler"], "SamplerConfig")
    assert sys.modules["core.sampler"].SamplerConfig is cls
    # Re-installing must return the *same* class (idempotent).
    cls2 = _install_checkpoint_compat()
    assert cls2 is cls


def test_install_checkpoint_compat_shim_marks_class_as_empty() -> None:
    """The shim class has no methods or attributes beyond ``pass``
    because the upstream's own shim is exactly ``class SamplerConfig:
    pass`` — the class is never called at runtime, only its qualified
    name is referenced by ``torch.load``."""
    from adaptive_reflow.adapters.lineageflow import _install_checkpoint_compat

    cls = _install_checkpoint_compat()
    # Empty body class - no callable members beyond the implicit
    # object inheritance.
    own_callables = {
        name
        for name in dir(cls)
        if name not in {"__class__", "__dict__", "__doc__", "__module__",
                        "__qualname__", "__weakref__"}
        and callable(getattr(cls, name, None))
    }
    # No public methods are defined on the empty shim.
    assert "sample" not in own_callables
    assert "forward" not in own_callables


def test_shim_unblocks_torch_load_on_real_ckpt() -> None:
    """End-to-end: with the shim installed, ``torch.load`` can resolve
    the pickled ``core.sampler.SamplerConfig`` class reference in the
    published ``lineageflow-rp55.ckpt``.

    This test is gated on both ``torch`` availability AND the
    downloaded ckpt presence so it skips gracefully on CPU-only /
    ckpt-absent environments. When the ckpt is absent the test
    confirms the shim install alone does not raise.
    """
    if not torch_is_available():
        pytest.skip("torch not installed in this environment")
    import torch

    from adaptive_reflow.adapters.lineageflow import (
        _install_checkpoint_compat,
        lineageflow_resolve_weights_path,
    )

    _install_checkpoint_compat()
    p = lineageflow_resolve_weights_path()
    if p is None or not p.exists():
        pytest.skip(
            "lineageflow-rp55.ckpt not present at data/lineageflow/ "
            "(download from HF before running this test)"
        )
    state = torch.load(str(p), map_location="cpu", weights_only=False)
    sd = state.get("state_dict", state)
    assert isinstance(sd, dict)
    # Paper headline: word_embeddings shape = (33, 1280).
    w = sd.get("model.encoder.embeddings.word_embeddings.weight")
    if w is None:
        w = sd.get("encoder.embeddings.word_embeddings.weight")
    assert w is not None, (
        "real ckpt missing the encoder word_embeddings tensor — "
        "structural mismatch with the published paper."
    )
    assert tuple(w.shape) == (33, 1280), (
        f"unexpected word_embeddings shape {tuple(w.shape)}; "
        "paper says (33, 1280)."
    )


# ---------------------------------------------------------------------------
# per_position_entropy_reduction (Wave 45 — P2-W33-C metric promotion)
# ---------------------------------------------------------------------------


def _solved_trace(adapter: LineageFlowAdapter, *, tag: str = "e0"):
    """Run one synthetic solve and return its trace."""
    bundle = adapter.build_initial_state(batch_id=tag, sample_id=tag)
    delta = adapter.compose_condition(bundle, _make_delta(target_round=1))
    return adapter.solve_ode(bundle, delta, seed=42)


def _overwrite_trajectory(
    adapter: LineageFlowAdapter, trace, theta0: np.ndarray, theta1: np.ndarray,
) -> None:
    """Pin the cached trajectory to a controlled ``(2, L, K)`` pair.

    Lets the entropy tests assert exact analytic values instead of
    whatever the synthetic velocity field happens to produce.
    """
    traj = np.empty((2, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64)
    traj[0] = theta0
    traj[1] = theta1
    adapter._native_states[trace.native_state_digest]["trajectory"] = traj


def _uniform_theta() -> np.ndarray:
    return np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE)


def _spike_theta() -> np.ndarray:
    theta = np.zeros(LINEAGEFLOW_STATE_SHAPE, dtype=np.float64)
    theta[:, 0] = 1.0
    return theta


def test_entropy_reduction_uniform_to_spike_equals_log_k() -> None:
    """Uniform prior collapsing to a one-hot endpoint reduces entropy by log K.

    This is the calibration anchor for the P2-W33-C metric
    (``docs/theory/operating-regime.md`` §11): the maximum achievable
    reduction is exactly ``log K``.

    It is also the **regression test for the double-normalisation bug**.
    LineageFlow's trajectory is already row-normalised, while the shared
    helper softmaxes its inputs as logits, so the adapter must convert
    via ``_theta_to_logits`` first. Dropping that conversion feeds
    probabilities into a softmax and collapses this assertion from
    3.4965 to 0.0275 — a 127x understatement that would leave the
    metric near-degenerate.
    """
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _uniform_theta(), _spike_theta())

    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(
        float(np.log(LINEAGEFLOW_VOCAB_SIZE)), abs=1e-6,
    )


def test_entropy_reduction_spike_to_uniform_is_negative_log_k() -> None:
    """The metric is signed: widening the posterior scores -log K."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _spike_theta(), _uniform_theta())

    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(
        -float(np.log(LINEAGEFLOW_VOCAB_SIZE)), abs=1e-6,
    )


def test_entropy_reduction_identical_endpoints_is_zero() -> None:
    """No change in the categorical means no entropy reduction."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _uniform_theta(), _uniform_theta())

    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(0.0, abs=1e-12)


def test_entropy_reduction_on_real_trajectory_is_bounded_and_nondegenerate() -> None:
    """The synthetic field produces a finite, in-bounds, non-saturated value."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)

    out = adapter.observe_entropy_reduction(trace, None)
    assert set(out) == {PER_POSITION_ENTROPY_REDUCTION}
    value = out[PER_POSITION_ENTROPY_REDUCTION]

    log_k = float(np.log(LINEAGEFLOW_VOCAB_SIZE))
    assert np.isfinite(value)
    assert -log_k - 1e-9 <= value <= log_k + 1e-9
    # P2-W33-C requires a *discriminating* metric: a value pinned at 0
    # or saturated at the log K bound carries no framework-vs-baseline
    # signal. The synthetic field must land strictly inside.
    assert abs(value) > 1e-6
    assert abs(value) < log_k - 1e-6


def test_entropy_reduction_reference_theta_mode() -> None:
    """An explicit reference replaces ``trajectory[0]`` as the baseline."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _spike_theta(), _spike_theta())

    # Within-trajectory: spike -> spike is a zero reduction.
    within = adapter.observe_entropy_reduction(trace, None)
    assert within[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(0.0, abs=1e-12)

    # Against a uniform baseline the same endpoint scores the full log K.
    against = adapter.observe_entropy_reduction(
        trace, None, reference_theta=_uniform_theta(),
    )
    assert against[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(
        float(np.log(LINEAGEFLOW_VOCAB_SIZE)), abs=1e-6,
    )


def test_entropy_reduction_is_deterministic() -> None:
    """Repeated calls on one trace are byte-identical (no RNG in the path)."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)

    first = adapter.observe_entropy_reduction(trace, None)
    second = adapter.observe_entropy_reduction(trace, None)
    assert first == second

    # And a second adapter solving the same inputs agrees exactly.
    other = _make_adapter(num_steps=4)
    other_trace = _solved_trace(other)
    assert (
        other.observe_entropy_reduction(other_trace, None)
        == first
    )


def test_entropy_reduction_ignores_paper_quantities() -> None:
    """``paper_quantities`` is signature-parity only; it must not change the value."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)

    baseline = adapter.observe_entropy_reduction(trace, None)
    assert adapter.observe_entropy_reduction(trace, object()) == baseline


def test_entropy_reduction_missing_native_state_raises() -> None:
    """A digest outside the LRU cache raises rather than returning a bogus number."""
    from adaptive_reflow.universal.state import ODEIntegratorTrace

    adapter = _make_adapter(num_steps=4)
    bogus = ODEIntegratorTrace(
        steps=1, accept_rate=1.0,
        native_state_digest="bogus", integrator_config_hash="bogus",
    )
    with pytest.raises(CapabilityMissingError):
        adapter.observe_entropy_reduction(bogus, None)


def test_entropy_reduction_matches_shared_helper() -> None:
    """The adapter re-derives nothing: it delegates to ``_adapter_common``."""
    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )
    from adaptive_reflow.adapters.lineageflow import _theta_to_logits

    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    traj = adapter.export_trajectory(trace)
    assert traj is not None

    expected = per_position_entropy_reduction(
        _theta_to_logits(traj[0]), _theta_to_logits(traj[-1]),
    )
    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == expected


def test_per_position_entropy_reduction_constant_is_exported() -> None:
    """The metric key is a stable public name a duck-typed caller can import."""
    import adaptive_reflow.adapters.lineageflow as lf

    assert PER_POSITION_ENTROPY_REDUCTION == "per_position_entropy_reduction"
    assert "PER_POSITION_ENTROPY_REDUCTION" in lf.__all__


# ---------------------------------------------------------------------------
# LineageFlowClassifierAwareRestart (Wave 45 Agent G)
# ---------------------------------------------------------------------------


def test_classifier_aware_restart_policy_is_importable() -> None:
    """The policy class is a stable public name a duck-typed caller can import."""
    import adaptive_reflow.adapters.lineageflow as lf
    from adaptive_reflow.adapters.lineageflow import (
        LineageFlowClassifierAwareRestart,
    )

    assert "LineageFlowClassifierAwareRestart" in lf.__all__
    assert lf.LineageFlowClassifierAwareRestart is LineageFlowClassifierAwareRestart
    # The audit code constants exist and are distinct.
    assert (
        lf.AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART
        == "lineageflow_classifier_aware_restart"
    )
    assert (
        lf.AUDIT_LINEAGEFLOW_CLASSIFIER_UNAVAILABLE
        == "lineageflow_classifier_unavailable"
    )


def test_classifier_aware_restart_proxy_is_deterministic_and_bounded() -> None:
    """The adapter-internal proxy uses max-prob per position, bounded in [1/(2K), 1]."""
    from adaptive_reflow.adapters.lineageflow import (
        LineageFlowClassifierAwareRestart,
        _lineageflow_classifier_confidence_proxy,
    )

    policy = LineageFlowClassifierAwareRestart(enable_upstream_probe=False)
    # Spike: every position has probability 1 on vocab index 0 → max = 1.0.
    spike = np.zeros(LINEAGEFLOW_STATE_SHAPE, dtype=np.float64)
    spike[:, 0] = 1.0
    conf = _lineageflow_classifier_confidence_proxy(spike)
    assert conf.shape == (LINEAGEFLOW_STATE_SHAPE[0],)
    assert np.all(conf == pytest.approx(1.0, abs=1e-9))
    # Uniform: max = 1/K → proxy is in [1/(2K), 1].
    uniform = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE)
    conf_uniform = _lineageflow_classifier_confidence_proxy(uniform)
    assert np.all(conf_uniform >= 1.0 / (2 * LINEAGEFLOW_VOCAB_SIZE) - 1e-9)
    assert np.all(conf_uniform <= 1.0 + 1e-9)
    # Determinism — same theta gives same proxy twice.
    assert np.array_equal(conf, _lineageflow_classifier_confidence_proxy(spike))


def test_classifier_aware_restart_propose_restart_mass_preserving() -> None:
    """``mean(m_vec) == base_memory_fraction`` (mass-preserving)."""
    from adaptive_reflow.adapters.lineageflow import (
        LineageFlowClassifierAwareRestart,
    )

    policy = LineageFlowClassifierAwareRestart(enable_upstream_probe=False)
    spike = np.zeros(LINEAGEFLOW_STATE_SHAPE, dtype=np.float64)
    spike[:, 0] = 1.0
    for base in (0.0, 0.25, 0.5, 0.75, 1.0):
        m_vec = policy.propose_restart(
            trace=None,
            paper_quantities=None,
            base_memory_fraction=float(base),
            theta=spike,
        )
        assert m_vec.shape == (LINEAGEFLOW_STATE_SHAPE[0],)
        assert np.all(m_vec >= 0.0)
        assert np.all(m_vec <= 1.0)
        # Mass-preserving: the mean equals the scalar base.
        assert m_vec.mean() == pytest.approx(float(base), abs=1e-9)


def test_classifier_aware_restart_uniform_theta_is_identity() -> None:
    """Uniform theta ⇒ per-position bias is zero ⇒ m_vec is the scalar broadcast."""
    from adaptive_reflow.adapters.lineageflow import (
        LineageFlowClassifierAwareRestart,
    )

    policy = LineageFlowClassifierAwareRestart(enable_upstream_probe=False)
    uniform = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE)
    for base in (0.1, 0.5, 0.9):
        m_vec = policy.propose_restart(
            trace=None,
            paper_quantities=None,
            base_memory_fraction=float(base),
            theta=uniform,
        )
        # All positions have identical confidence ⇒ deviation cancels ⇒
        # m_vec is exactly the scalar base at every position.
        assert np.all(m_vec == pytest.approx(float(base), abs=1e-12))


def test_classifier_aware_restart_alpha_zero_disables_bias() -> None:
    """``alpha == 0`` reduces the policy to today's scalar blend."""
    from adaptive_reflow.adapters.lineageflow import (
        LineageFlowClassifierAwareRestart,
    )

    spike = np.zeros(LINEAGEFLOW_STATE_SHAPE, dtype=np.float64)
    spike[:, 0] = 1.0
    for alpha in (0.0, 0.0):
        policy = LineageFlowClassifierAwareRestart(
            alpha=alpha, enable_upstream_probe=False,
        )
        m_vec = policy.propose_restart(
            trace=None,
            paper_quantities=None,
            base_memory_fraction=0.4,
            theta=spike,
        )
        assert np.all(m_vec == pytest.approx(0.4, abs=1e-12))


def test_classifier_aware_restart_spike_biases_confident_positions_higher() -> None:
    """With a spike (high confidence) and alpha > 0, biased positions exceed base."""
    from adaptive_reflow.adapters.lineageflow import (
        LineageFlowClassifierAwareRestart,
    )

    spike = np.zeros(LINEAGEFLOW_STATE_SHAPE, dtype=np.float64)
    spike[:, 0] = 1.0
    policy = LineageFlowClassifierAwareRestart(
        alpha=1.0, enable_upstream_probe=False,
    )
    m_vec = policy.propose_restart(
        trace=None,
        paper_quantities=None,
        base_memory_fraction=0.5,
        theta=spike,
    )
    # With a spike the confidence vector is constant (all 1.0), so the
    # centre-subtraction cancels and m_vec is exactly base. This is the
    # correct mass-preserving behaviour and confirms the policy never
    # amplifies a flat signal — only signals with per-position
    # variation produce variation in m_vec.
    assert np.all(m_vec == pytest.approx(0.5, abs=1e-12))

    # Now build a *mixed* signal: half positions are spike (confident),
    # half are uniform (uncertain). The centre-subtracted confidence
    # is non-trivial, so m_vec must vary.
    mixed = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE)
    L = LINEAGEFLOW_STATE_SHAPE[0]
    mixed[: L // 2] = spike[: L // 2]
    m_vec_mixed = policy.propose_restart(
        trace=None,
        paper_quantities=None,
        base_memory_fraction=0.5,
        theta=mixed,
    )
    assert m_vec_mixed.shape == (L,)
    # The confident half should bias above the base; the uncertain
    # half should bias below. This is the load-bearing asymmetry the
    # policy introduces.
    assert m_vec_mixed[: L // 2].mean() > 0.5
    assert m_vec_mixed[L // 2 :].mean() < 0.5


def test_classifier_aware_restart_off_by_default_preserves_legacy_blend() -> None:
    """Default ``classifier_aware_restart=False`` keeps scalar blend behaviour.

    Regression guard for Wave 45 Agent G: flipping the flag must NOT
    alter the result of :meth:`apply_restart_distribution` for any of
    the 22 existing tests when the flag is at its default. The test
    asserts the legacy per-position scalar (``prior_theta + (1 - m) *
    fresh_theta`` row-wise broadcast) remains in force and the audit
    code stays at the legacy ``AUDIT_LINEAGEFLOW_RESTART_BLEND``.
    """
    from adaptive_reflow.adapters.lineageflow import (
        AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART,
    )

    adapter = _make_adapter(num_steps=2)
    bundle = adapter.build_initial_state(batch_id="b_w45g_off", sample_id="s_w45g_off")
    policy = FinalRestartPolicy(
        policy_id=PolicyId("wave45-agent-g-default-off"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("test-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.5)},
        alpha_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(1.0)},
        fresh_noise_floor_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={AMINO_ACID_CATEGORICAL: True},
        ledger_row_id=LedgerRowId("ledger-wave45-agent-g-off"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    restarted = adapter.apply_restart_distribution(bundle, policy)
    # Provenance has the legacy audit code and NOT the new one —
    # the classifier-aware flag is off by default.
    assert AUDIT_LINEAGEFLOW_RESTART_BLEND in restarted.provenance
    assert AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART not in restarted.provenance
    # The result is still a valid probability distribution (row-normalised).
    restarted_theta = adapter._native_states[restarted.native_state_digest]["theta"]
    row_sums = restarted_theta.sum(axis=-1)
    assert np.allclose(row_sums, 1.0, atol=1e-6)


def test_classifier_aware_restart_on_flips_audit_code_and_uses_per_position() -> None:
    """Opt-in flag activates the policy: audit code + per-position broadcast."""
    from adaptive_reflow.adapters.lineageflow import (
        AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART,
    )

    adapter = _make_adapter(
        num_steps=2, classifier_aware_restart=True, classifier_alpha=1.0,
    )
    bundle = adapter.build_initial_state(batch_id="b_w45g_on", sample_id="s_w45g_on")
    policy = FinalRestartPolicy(
        policy_id=PolicyId("wave45-agent-g-on"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("test-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.5)},
        alpha_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(1.0)},
        fresh_noise_floor_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={AMINO_ACID_CATEGORICAL: True},
        ledger_row_id=LedgerRowId("ledger-wave45-agent-g-on"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    restarted = adapter.apply_restart_distribution(bundle, policy)
    # Both audit codes are present in provenance.
    assert AUDIT_LINEAGEFLOW_RESTART_BLEND in restarted.provenance
    assert AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART in restarted.provenance
    # The result is still a valid probability distribution (row-normalised).
    restarted_theta = adapter._native_states[restarted.native_state_digest]["theta"]
    row_sums = restarted_theta.sum(axis=-1)
    assert np.allclose(row_sums, 1.0, atol=1e-6)
    # Policy instance is now created on the adapter (lazy init).
    assert adapter._classifier_aware_restart_policy is not None


# ---------------------------------------------------------------------------
# F-4 dtype boundary fix (Wave 47 Agent B)
# ---------------------------------------------------------------------------


def test_torch_velocity_field_returns_correct_shape_and_dtype_with_esm() -> None:
    """F-4 fix regression test: ``_torch_velocity_field`` must accept
    a (L, K=33) float simplex and return a (L, K=33) float64 tensor
    without raising the embedding dtype error from
    ``docs/audit/wave45-final-eval.md`` §"LineageFlow pre-existing
    bug" (``Expected tensor for argument #1 'indices' to have one of
    the following scalar types: Long, Int; but got torch.FloatTensor``).

    The test uses the bare HuggingFace ``EsmModel`` (same loader as
    ``_load_torch_model`` in production) so the dtype-boundary fix
    is exercised end-to-end: argmax → ``.long()`` → ``input_ids=``
    on the encoder. The bare encoder has no flow head, so the
    fix-degraded output is a zero (B, L, K) projection that still
    satisfies the shape contract.
    """
    pytest.importorskip("torch")
    pytest.importorskip("transformers")

    from transformers import EsmModel  # type: ignore[import-not-found]

    from adaptive_reflow.adapters.lineageflow import (
        LINEAGEFLOW_FAMILY_EMBED_DIM,
        _torch_velocity_field,
    )

    torch = pytest.importorskip("torch")
    model = EsmModel.from_pretrained(
        "facebook/esm2_t33_650M_UR50D",
        ignore_mismatched_sizes=True,
    )
    model.eval()

    # Build a uniform (L, K=33) per-position simplex with a small
    # bias toward index 0 so argmax is non-trivial.
    x = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE,
                dtype=np.float64)
    x[:, 0] = 0.5
    cache = {
        "family_embed": np.zeros(LINEAGEFLOW_FAMILY_EMBED_DIM, dtype=np.float64),
    }

    out = _torch_velocity_field(
        model=model,
        x=x,
        t=0.5,
        dtype=torch.float32,
        cache=cache,
        guidance_scale=1.0,
    )

    # Shape contract: (L, K) float64, matching LINEAGEFLOW_STATE_SHAPE.
    assert out.shape == LINEAGEFLOW_STATE_SHAPE
    assert out.dtype == np.float64
    # All values must be finite (the dtype-boundary fix must NOT
    # introduce NaN / Inf via a bad projection).
    assert np.isfinite(out).all()


def test_torch_velocity_field_dtype_argmax_long_does_not_raise() -> None:
    """F-4 fix regression test: the argmax + ``.long()`` conversion
    on a uniform (L, K=33) simplex must NOT raise
    ``RuntimeError: Expected tensor for argument #1 'indices' to have
    one of the following scalar types: Long, Int``. This is the
    narrowest possible regression test for the dtype boundary
    documented in Wave 45 Agent H §"LineageFlow pre-existing bug".
    """
    pytest.importorskip("torch")
    pytest.importorskip("transformers")

    from transformers import EsmModel  # type: ignore[import-not-found]

    from adaptive_reflow.adapters.lineageflow import (
        LINEAGEFLOW_FAMILY_EMBED_DIM,
        _torch_velocity_field,
    )

    torch = pytest.importorskip("torch")
    model = EsmModel.from_pretrained(
        "facebook/esm2_t33_650M_UR50D",
        ignore_mismatched_sizes=True,
    )
    model.eval()

    # Uniform simplex (no spikes); argmax returns 0 for every row.
    x = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE,
                dtype=np.float64)
    cache = {
        "family_embed": np.zeros(LINEAGEFLOW_FAMILY_EMBED_DIM, dtype=np.float64),
    }

    # The exact call from ``solve_ode`` -> ``_velocity_field`` ->
    # ``_torch_velocity_field`` must succeed (no embedding dtype
    # error, no TypeError on unexpected kwargs).
    try:
        out = _torch_velocity_field(
            model=model,
            x=x,
            t=0.25,
            dtype=torch.float32,
            cache=cache,
            guidance_scale=1.0,
        )
    except RuntimeError as exc:
        msg = str(exc)
        assert "indices" not in msg or "Long" not in msg, (
            f"F-4 fix regression: dtype boundary still raises "
            f"embedding indices error: {msg!r}"
        )
        raise
    except TypeError as exc:
        pytest.fail(
            f"F-4 fix regression: model signature mismatch "
            f"(unexpected kwarg): {exc!r}"
        )

    assert out.shape == LINEAGEFLOW_STATE_SHAPE


# ---------------------------------------------------------------------------
# Wave 59 Agent 4 — PerturbationPolicy wiring
# ---------------------------------------------------------------------------


def _w59_restart_policy(run_suffix: str) -> FinalRestartPolicy:
    """Build the canonical beta=0.5 restart policy used by Wave 59 tests."""
    return FinalRestartPolicy(
        policy_id=PolicyId("uniform-beta-0.5"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(f"test-run-{run_suffix}"),
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


def test_lineageflow_default_perturbation_is_uniform_fresh() -> None:
    """No-arg constructor installs :class:`UniformFreshPerturbation`.

    Wave 59 Agent 4 acceptance: the DEFAULT must stay the legacy
    uniform-fresh policy so Wave 47 / 52 / 58 composite data is
    preserved.
    """
    adapter = _make_adapter()
    assert isinstance(adapter._perturbation, UniformFreshPerturbation)
    assert adapter._perturbation.seed_offset == 0


def test_lineageflow_default_perturbation_preserves_legacy_restart_blend() -> None:
    """Default (implicit) == explicit UniformFresh == pinned legacy blend.

    The blend is recomputed here from first principles with the
    PRESERVED ``(policy_hash, source_round)`` seed so a future
    refactor of the perturbation seam cannot silently rotate the
    noise stream.
    """
    import hashlib

    from adaptive_reflow.adapters.lineageflow import (
        _synthesize_latent_like_tensor,
    )

    policy = _w59_restart_policy("w59-default")

    implicit = _make_adapter()
    bundle_i = implicit.build_initial_state(
        batch_id="w59_default", sample_id="s_w59"
    )
    restarted_i = implicit.apply_restart_distribution(bundle_i, policy)

    explicit = _make_adapter(perturbation=UniformFreshPerturbation())
    bundle_e = explicit.build_initial_state(
        batch_id="w59_default", sample_id="s_w59"
    )
    restarted_e = explicit.apply_restart_distribution(bundle_e, policy)

    # 1. Implicit default and explicit UniformFresh agree bit-for-bit.
    assert restarted_i.native_state_digest == restarted_e.native_state_digest
    th_i = implicit._native_states[restarted_i.native_state_digest]["theta"]
    th_e = explicit._native_states[restarted_e.native_state_digest]["theta"]
    assert np.array_equal(np.asarray(th_i), np.asarray(th_e))

    # 2. Both match the legacy inline recomputation.
    prior_theta = np.asarray(
        implicit._native_states[bundle_i.native_state_digest]["theta"],
        dtype=np.float64,
    ).reshape(LINEAGEFLOW_STATE_SHAPE)
    next_round = int(bundle_i.source_round) + 1
    seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
    seed = int(hashlib.sha256(seed_blob).hexdigest()[:8], 16)
    fresh_theta = _synthesize_latent_like_tensor(np.random.default_rng(seed))
    expected = (0.5 * prior_theta + 0.5 * fresh_theta).astype(np.float64)
    expected = expected / np.maximum(expected.sum(axis=-1, keepdims=True), 1e-30)
    expected = np.clip(expected, 0.0, LINEAGEFLOW_CLAMP)
    expected = expected / np.maximum(expected.sum(axis=-1, keepdims=True), 1e-30)
    assert np.array_equal(np.asarray(th_i, dtype=np.float64), expected)

    # 3. The legacy default emits NO new audit code.
    assert AUDIT_LINEAGEFLOW_PERTURBATION_POLICY not in restarted_i.provenance
    assert AUDIT_LINEAGEFLOW_RESTART_BLEND in restarted_i.provenance


def test_lineageflow_brai_perturbation_is_opt_in_and_changes_restart() -> None:
    """Passing BRAI routes the restart through the attractor-inversion path.

    The prior native-state entry carries an ``e_rho`` paper-quantity
    snapshot, so :class:`PaperQuantityAttractorInversion` uses the
    analytic Gaussian gradient (``fresh_raw = x + eps * x / sigma^2``),
    which the adapter then projects back onto the per-position simplex.
    """
    policy = _w59_restart_policy("w59-brai")
    brai = PaperQuantityAttractorInversion(eps_scale=0.25, default_sigma=1.0)
    adapter = _make_adapter(perturbation=brai)
    bundle = adapter.build_initial_state(batch_id="w59_brai", sample_id="s_brai")
    prior_entry = adapter._native_states[bundle.native_state_digest]
    prior_entry["paper_quantities"] = {"e_rho": 1.0}
    prior_theta = np.asarray(prior_entry["theta"], dtype=np.float64).reshape(
        LINEAGEFLOW_STATE_SHAPE
    )

    restarted = adapter.apply_restart_distribution(bundle, policy)

    # BRAI path is recorded in provenance.
    assert AUDIT_LINEAGEFLOW_PERTURBATION_POLICY in restarted.provenance

    # Recompute: BRAI proposal, simplex projection, blend, renormalise.
    proposed = prior_theta + 0.25 * prior_theta
    proposed = np.clip(proposed, 0.0, None)
    fresh_theta = proposed / np.maximum(
        proposed.sum(axis=-1, keepdims=True), 1e-30
    )
    expected = (0.5 * prior_theta + 0.5 * fresh_theta).astype(np.float64)
    expected = expected / np.maximum(expected.sum(axis=-1, keepdims=True), 1e-30)
    expected = np.clip(expected, 0.0, LINEAGEFLOW_CLAMP)
    expected = expected / np.maximum(expected.sum(axis=-1, keepdims=True), 1e-30)
    got = np.asarray(
        adapter._native_states[restarted.native_state_digest]["theta"],
        dtype=np.float64,
    )
    assert np.allclose(got, expected)
    # The result is still a valid per-position categorical.
    assert np.allclose(got.sum(axis=-1), 1.0)


def test_lineageflow_constructor_rejects_non_perturbation_policy() -> None:
    """A non-policy ``perturbation`` arg surfaces a ``TypeError``."""
    with pytest.raises(TypeError, match="perturbation_must_implement"):
        _make_adapter(perturbation="not-a-policy")  # type: ignore[arg-type]
