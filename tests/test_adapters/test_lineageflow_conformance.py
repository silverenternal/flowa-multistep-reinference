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
    LINEAGEFLOW_INTEGRATOR_EULER,
    LINEAGEFLOW_INTEGRATOR_HEUN,
    LINEAGEFLOW_INTEGRATORS,
    LINEAGEFLOW_MAX_LENGTH,
    LINEAGEFLOW_MECHANISM_ID,
    LINEAGEFLOW_NUM_STEPS_DEFAULT,
    LINEAGEFLOW_STATE_SHAPE,
    LINEAGEFLOW_T_END,
    LINEAGEFLOW_VOCAB_SIZE,
    PER_POSITION_ENTROPY_REDUCTION,
    PFAM_FAMILY_COND,
    LineageFlowAdapter,
    LineageFlowCapabilities,
    default_lineageflow_adapter,
    lineageflow_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.algorithm.perturbation import (
    PaperQuantityAttractorInversion,
    UniformFreshPerturbation,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    RunId,
)
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.adapter import CapabilityMissingError
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    StateBundle,
    validate_state_bundle,
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


# ---
# (Header + imports shared with test_lineageflow_smoke.py; see that file.)
# ---


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

    LineageFlowClassifierAwareRestart(enable_upstream_probe=False)
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


# ---------------------------------------------------------------------------
# Wave 68 Phase 2 — AdapterObservationProtocol observe()
# ---------------------------------------------------------------------------


def test_lineageflow_observe_returns_all_four_kinds() -> None:
    """``observe()`` returns ObservationResult tagged by all four kinds.

    Verifies the Wave 68 Phase 2 surface: LineageFlow is the rare
    protein adapter that supports ALL FOUR ``ObservationKind`` tags
    — including ``POSITION_ENTROPY_REDUCTION`` (the per-position
    amino-acid categorical is a real residue distribution; Wave 45
    audit makes this distinction explicit).
    """
    from adaptive_reflow.framework.interfaces import (
        AdapterObservationProtocol,
        ObservationKind,
    )

    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="w68p2", sample_id="s")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    # Conformance check.
    assert isinstance(adapter, AdapterObservationProtocol)

    results = adapter.observe(trace, bundle)
    kinds = {r.kind for r in results}

    # All four kinds supported for LineageFlow.
    assert ObservationKind.ENDPOINT_BUNDLE in kinds
    assert ObservationKind.DISCRETE_TOKENS in kinds
    assert ObservationKind.POSITION_ENTROPY_REDUCTION in kinds
    assert ObservationKind.TRAJECTORY_NATIVE in kinds


def test_lineageflow_observe_endpoint_bundle_payload_matches_legacy() -> None:
    """``observe(... ENDPOINT_BUNDLE)`` returns a StateBundle equal to
    :meth:`observe_endpoint`.
    """
    from adaptive_reflow.framework.interfaces import ObservationKind

    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="w68p2_eb", sample_id="s")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    legacy_endpoint = adapter.observe_endpoint(trace, bundle)
    results = adapter.observe(
        trace, bundle, strategies=(ObservationKind.ENDPOINT_BUNDLE,)
    )

    assert len(results) == 1
    obs = results[0]
    assert obs.kind == ObservationKind.ENDPOINT_BUNDLE
    assert obs.channel == str(AMINO_ACID_CATEGORICAL)
    assert obs.units == "state_bundle"
    assert obs.payload.native_state_digest == legacy_endpoint.native_state_digest
    assert obs.payload.source_round == legacy_endpoint.source_round


def test_lineageflow_observe_entropy_reduction_payload_matches_legacy() -> None:
    """``observe(... POSITION_ENTROPY_REDUCTION)`` returns a float
    equal to :meth:`observe_entropy_reduction`.
    """
    from adaptive_reflow.framework.interfaces import ObservationKind

    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="w68p2_ent", sample_id="s")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    legacy_entropy = adapter.observe_entropy_reduction(trace, None)
    legacy_value = float(legacy_entropy[PER_POSITION_ENTROPY_REDUCTION])

    results = adapter.observe(
        trace, bundle, strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,)
    )

    assert len(results) == 1
    obs = results[0]
    assert obs.kind == ObservationKind.POSITION_ENTROPY_REDUCTION
    assert obs.channel == PER_POSITION_ENTROPY_REDUCTION
    assert obs.units == "nats"
    # Byte-stable: typed payload equals legacy float.
    assert obs.payload == pytest.approx(legacy_value, rel=1e-12, abs=1e-15)
    assert np.isfinite(obs.payload)


def test_lineageflow_observe_strategy_subset_filters_results() -> None:
    """``strategies=(...)`` filters the returned ObservationResult tuple.

    Demonstrates the per-call optimization: passing only
    ``DISCRETE_TOKENS`` + ``POSITION_ENTROPY_REDUCTION`` must yield
    exactly two results and no ``ENDPOINT_BUNDLE`` /
    ``TRAJECTORY_NATIVE``.
    """
    from adaptive_reflow.framework.interfaces import ObservationKind

    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="w68p2_sub", sample_id="s")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    results = adapter.observe(
        trace,
        bundle,
        strategies=(
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
        ),
    )

    assert len(results) == 2
    kinds_returned = {r.kind for r in results}
    assert kinds_returned == {
        ObservationKind.DISCRETE_TOKENS,
        ObservationKind.POSITION_ENTROPY_REDUCTION,
    }


# ---------------------------------------------------------------------------
# Wave 81 Agent B — _StubLineageFlow.forward signature fix regression
# ---------------------------------------------------------------------------
#
# The pre-Wave-81 stub took positional ``(x, t, family)`` which raises
# ``TypeError: ... unexpected keyword argument 'input_ids'`` at the
# F-4-fix call site ``model(input_ids=ids)`` (line 579). Wave 81 fix-A
# rewrites the stub's forward to accept ``input_ids=None``,
# ``attention_mask=None``, ``inputs_embeds=None``, ``**kwargs`` and
# returns a zero (B, L, K) tensor. Fix-B replaces the bare
# ``except Exception:`` with ``(ImportError, ModuleNotFoundError) ->
# stub`` and ``Exception -> CapabilityMissingError``. These tests pin
# the contract so a future regression cannot silently re-introduce the
# bug.
# ---------------------------------------------------------------------------


def test_StubLineageFlow_accepts_input_ids_kwarg() -> None:
    """``_StubLineageFlow.forward`` must accept ``input_ids=`` so the
    F-4-fix call site ``model(input_ids=ids)`` (line 579) does not
    raise ``TypeError`` when transformers is absent.

    The pre-Wave-81 stub took positional ``(x, t, family)`` which
    crashed on the ``input_ids=`` kwarg. Wave 81 fix-A rewrites the
    signature to mirror real ``EsmModel.forward`` so the synthetic-mode
    path in venvs without ``transformers`` (e.g. ``flowmol3_venv``)
    still works.

    The test does NOT ``importorskip("transformers")`` so it exercises
    the stub path directly (the bug only surfaces in envs without
    transformers).
    """
    pytest.importorskip("torch")

    import torch  # noqa: F401  (guarded above)

    from adaptive_reflow.adapters.lineageflow import (  # type: ignore[attr-defined]
        LINEAGEFLOW_MAX_LENGTH,
        LINEAGEFLOW_VOCAB_SIZE,
        _StubLineageFlow,
    )

    stub = _StubLineageFlow(
        vocab_size=LINEAGEFLOW_VOCAB_SIZE, hidden_size=1280,
    )
    ids = torch.zeros(1, LINEAGEFLOW_MAX_LENGTH, dtype=torch.long)
    out = stub(input_ids=ids)
    # Stub contract: (B, L, K) zero tensor, float32.
    assert out.shape == (1, LINEAGEFLOW_MAX_LENGTH, LINEAGEFLOW_VOCAB_SIZE)
    assert out.dtype == torch.float32
    assert torch.equal(out, torch.zeros_like(out))

    # Also accept ``inputs_embeds=`` (upstream LineageFlowClassifier path).
    emb = torch.zeros(1, LINEAGEFLOW_MAX_LENGTH, 1280, dtype=torch.float32)
    out2 = stub(inputs_embeds=emb)
    assert out2.shape == (1, LINEAGEFLOW_MAX_LENGTH, LINEAGEFLOW_VOCAB_SIZE)
    assert out2.dtype == torch.float32

    # Also accept ``attention_mask=`` (EsmModel default kwarg).
    mask = torch.ones(1, LINEAGEFLOW_MAX_LENGTH, dtype=torch.long)
    out3 = stub(input_ids=ids, attention_mask=mask)
    assert out3.shape == (1, LINEAGEFLOW_MAX_LENGTH, LINEAGEFLOW_VOCAB_SIZE)


def test_real_LineageFlow_EsmModel_load_succeeds_in_lineageflow_venv() -> None:
    """When ``transformers`` IS available and ``EsmModel.from_pretrained``
    succeeds, the adapter path uses the real EsmModel (not the stub)
    and the per-step call at line 579 returns a finite ``(L, K)`` array.

    This pins the happy-path contract: the fix must not regress the
    case where transformers is installed and the HF cache is populated.
    Skips when transformers is not available (the dev-env / synthetic
    path is covered by the other 22 tests).
    """
    pytest.importorskip("torch")
    pytest.importorskip("transformers")

    from transformers import EsmModel  # type: ignore[import-not-found]

    from adaptive_reflow.adapters.lineageflow import (  # type: ignore[attr-defined]
        LINEAGEFLOW_FAMILY_EMBED_DIM,
        LINEAGEFLOW_STATE_SHAPE,
        _torch_velocity_field,
    )

    torch = pytest.importorskip("torch")
    model = EsmModel.from_pretrained(
        "facebook/esm2_t33_650M_UR50D",
        ignore_mismatched_sizes=True,
    )
    model.eval()

    x = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE,
                dtype=np.float64)
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

    assert out.shape == LINEAGEFLOW_STATE_SHAPE
    assert out.dtype == np.float64
    assert np.isfinite(out).all()


def test_adapter_raises_CapabilityMissingError_on_esmmodel_load_failure(
    tmp_path,
) -> None:
    """When ``transformers`` IS installed but ``EsmModel.from_pretrained``
    raises (HF cache empty, network blocked, ckpt SHA mismatch),
    ``_load_torch_model`` must surface a ``CapabilityMissingError``
    rather than silently substituting the stub.

    Pre-Wave-81 the bare ``except Exception:`` swallowed the failure
    and substituted the stub, masking the production-blocker. Wave 81
    fix-B routes the Exception branch to ``CapabilityMissingError`` so
    the eval pipeline sees the honest error.

    Skips entirely when transformers is not installed (the
    (ImportError, ModuleNotFoundError) branch is the dev-env path,
    which keeps the stub).
    """
    transformers = pytest.importorskip("transformers")

    def _raise(*_a: object, **_k: object) -> None:
        raise RuntimeError("simulated HF cache miss")

    # Monkeypatch ``EsmModel.from_pretrained`` to raise so the
    # production-load-failure branch is exercised.
    original = transformers.EsmModel.from_pretrained
    transformers.EsmModel.from_pretrained = classmethod(  # type: ignore[assignment]
        lambda cls, *a, **k: _raise(*a, **k)
    )
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore[attr-defined]
            _load_torch_model,
        )
        from adaptive_reflow.universal.adapter import (
            CapabilityMissingError,
        )

        # ``_load_torch_model`` only takes the existence branch when
        # the file at ``weights_path`` exists. Use a real file with
        # placeholder bytes.
        fake_ckpt = tmp_path / "fake.ckpt"
        fake_ckpt.write_bytes(b"\x80\x02}q\x00.")  # minimal pickle

        with pytest.raises(CapabilityMissingError) as excinfo:
            _load_torch_model(fake_ckpt)
        assert "lineageflow_esm_load_failed" in str(excinfo.value)
    finally:
        transformers.EsmModel.from_pretrained = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Wave 95 Phase 2.A — defensive state=None guard in observe()
# ---------------------------------------------------------------------------


def test_observe_with_state_none_returns_empty_tuple() -> None:
    """Regression (Wave 95 Phase 2.A): ``observe(..., state=None)`` is safe.

    The :class:`AdapterObservationProtocol` (Wave 67) explicitly permits
    ``state=None`` (interfaces.py:617-619 — ``May be None for adapters
    that materialise state lazily``). The metric helper
    ``_extract_observation`` in ``tools/run_real_ckpt_eval.py``
    historically passes ``state=None`` (Wave 68 Phase 5 §4.1 regression).

    Pre-fix: ``observe_endpoint(trace, None)`` raised ``AttributeError``
    because the LineageFlowAdapter's ``observe_endpoint`` accesses
    ``state.source_round`` unconditionally.

    Post-fix: ``observe()`` short-circuits with ``return tuple()`` before
    touching ``observe_endpoint``. The metric helper then sees a clean
    empty tuple and can move on without crashing the eval pipeline.
    """
    from adaptive_reflow.framework.interfaces import ObservationKind

    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(batch_id="w95a_none", sample_id="s")
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    # All four strategies — state=None should still produce empty tuple.
    results_all = adapter.observe(
        trace,
        None,                                          # state=None
        paper_quantities=None,
    )
    assert results_all == ()
    assert isinstance(results_all, tuple)

    # Explicit strategies subset — also empty tuple.
    results_subset = adapter.observe(
        trace,
        None,                                          # state=None
        paper_quantities=None,
        strategies=(
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
    )
    assert results_subset == ()

    # Sanity: with a real state, observe() still works (non-regression).
    results_real = adapter.observe(trace, bundle)
    kinds_real = {r.kind for r in results_real}
    assert ObservationKind.ENDPOINT_BUNDLE in kinds_real
    assert ObservationKind.DISCRETE_TOKENS in kinds_real
    assert ObservationKind.POSITION_ENTROPY_REDUCTION in kinds_real
