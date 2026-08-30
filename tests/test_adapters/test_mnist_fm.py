"""Comprehensive test suite for the MNIST rectified-flow adapter (EXP-1).

Mirrors the structure of :mod:`tests.test_adapters.test_twodim_fm`:
exercises :class:`adaptive_reflow.adapters.mnist_fm.MnistFmAdapter`
end-to-end against the trained UNet (``data/mnist_fm.npz``). The
adapter wraps a small velocity-field UNet (down + bottleneck + up;
``base_channels``-wide; ~500K-2M parameters) trained offline against
the MNIST 28x28 grayscale target.

Tests
-----

* ``test_load_npz_and_capabilities`` -- the canonical
  ``data/mnist_fm.npz`` exists; the capability handshake is well-formed
  (``state_shape=(784,)``, ``supported_channels=("x",)``,
  ``native_config_hash="mnist_fm:cfg:v1"``).
* ``test_adapter_loads_handshake`` -- every required engine-side
  capability flag is ``True``.
* ``test_adapter_satisfies_protocol`` -- the adapter passes
  :func:`isinstance` against the :class:`FlowMatchingODEAdapter`
  ``@runtime_checkable`` Protocol.
* ``test_run_round_produces_target_resembling_samples`` --
  ``Engine.run_round`` drives a round end-to-end; the endpoint is
  finite (no NaN) and inside the ``[-1, 1]^784`` clamp box.
* ``test_byte_determinism_across_runs`` -- two 10-round scenarios from
  identical seeds produce identical native-state digests.
* ``test_no_nan_over_many_seeds`` -- ``solve_ode`` returns finite
  endpoints for ``seed in {0, ..., 19}``.
* ``test_endpoint_shape_correct`` -- the native state stored under
  :attr:`observe_endpoint`'s digest resolves to a ``(784,)`` array.
* ``test_protocol_surface_intact`` -- every documented method is
  callable and non-mutating for canonical inputs.
* ``test_restart_blend_respects_memory_fraction`` --
  ``apply_restart_distribution`` behaves correctly for
  ``beta in {0.0, 0.5, 1.0}`` (full prior / midpoint / full fresh).
* ``test_engine_stress_20_rounds_with_restart`` -- ``Engine.run_round``
  drives 20 rounds alternating ``beta in {0.0, 0.5}``; every trace
  validates under a 120-second CPU budget.
* ``test_inject_forward_noise_hook`` -- ``inject_forward_noise`` adds
  the perturbation and stamps ``forward_noise_applied`` on provenance.

The conftest fixture ``_materialize_mnist_fm_weights`` materialises
the canonical ``data/mnist_fm.npz`` (training for 1 epoch on a 1000-
image subset) when the file is missing. Full-resolution training is
performed by ``tools/materialize_mnist_fm.py`` before the production
ablation runs.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

# Skip the entire file when torch is not installed in the test env.
# The R4 EXP-1 MNIST adapter depends on torch for the velocity-field UNet;
# without it, no test in this module can run. Mirrors the scikit-learn and
# Hugging Face transformers convention for optional-dependency tests.
pytest.importorskip("torch", reason="torch is required for MNIST FM tests (R4 EXP-1)")

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


def validate_round_trace(trace) -> tuple[bool, tuple[str, ...]]:
    """Mirror ``validate_round_trace`` from test_twodim_fm.py."""
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


MNIST_FM_CHANNELS: tuple[str, ...] = ("x",)


def _make_phase_state(*, horizon_remaining: int = 200):
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="mnist-fm-test-lineage",
        recorded_at_round=0,
    )


def _make_final_policy(
    *,
    policy_id: str,
    run_id: str,
    beta: float,
    channels: tuple[str, ...] = MNIST_FM_CHANNELS,
    target_round: int = 0,
    beta_from_schedule: bool = False,
):
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

    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ChannelName(k): FactorValue(float(beta)) for k in channels},
        alpha_by_channel={ChannelName(k): FactorValue(1.0) for k in channels},
        fresh_noise_floor_by_channel={ChannelName(k): FactorValue(0.0) for k in channels},
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName(k): True for k in channels},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=bool(beta_from_schedule),
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int = 20,
    source: str = "mnist_fm_test",
    calibration_artifact_hash: str = "cal-mnist-fm",
):
    from adaptive_reflow.frame import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={"num_steps": int(num_steps)},
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _native_x0(adapter, digest: str) -> np.ndarray:
    """Return the ``x0`` stored under ``digest`` as a flat ``(784,)`` float64 array."""
    native = adapter._native_states[digest]  # noqa: SLF001 — test seam
    return np.asarray(native["x0"], dtype=np.float64).reshape(784)


def _endpoint_from_trace(adapter, trace) -> np.ndarray:
    """Return the final trajectory point stored under ``trace.native_state_digest``."""
    native = adapter._native_states[trace.native_state_digest]  # noqa: SLF001
    traj = np.asarray(native["trajectory"], dtype=np.float64)
    return np.asarray(traj[-1], dtype=np.float64).reshape(784)


def _compute_fresh_x0(policy, source_round: int) -> np.ndarray:
    """Re-derive the fresh-noise prior the adapter would draw for ``(policy, source_round+1)``.

    Mirrors :meth:`MnistFmAdapter.apply_restart_distribution`'s
    clipping-to-``[-1, 1]`` so the test sees the *post-clip* fresh
    noise the adapter stores, not the raw ``N(0, I_784)`` draw.
    """
    next_round = int(source_round) + 1
    blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
    seed = int(hashlib.sha256(blob).hexdigest()[:8], 16)
    fresh = np.random.default_rng(seed).standard_normal(784).astype(np.float64)
    np.clip(fresh, -1.0, 1.0, out=fresh)
    return fresh.reshape(784)


# ---------------------------------------------------------------------------
# 1. Weights load; capabilities handshake is well-formed.
# ---------------------------------------------------------------------------


def test_load_npz_and_capabilities(mnist_fm_weights_path: Path) -> None:
    """Load ``data/mnist_fm.npz``; assert canonical shapes and capability handshake."""
    from adaptive_reflow.adapters.mnist_fm import (
        MNIST_FM_CONFIG_HASH,
        MnistFmAdapter,
    )
    from adaptive_reflow.adapters.mnist_fm_train import WEIGHT_KEYS
    from adaptive_reflow.universal.adapter import validate_capabilities

    with np.load(mnist_fm_weights_path) as data:
        keys = set(data.files)
        for key in WEIGHT_KEYS:
            assert key in keys, f"missing weight key {key!r}"
        # down1_w shape is (C, 2, 3, 3) where C = base_channels.
        down1_w = np.asarray(data["down1_w"], dtype=np.float64)
        # bottleneck_w shape is (2C, 2C, 3, 3) — verify second axis matches first.
        bottleneck_w = np.asarray(data["bottleneck_w"], dtype=np.float64)
        out_w = np.asarray(data["out_w"], dtype=np.float64)
    assert down1_w.ndim == 4 and down1_w.shape[1] == 2 and down1_w.shape[2] == 3 and down1_w.shape[3] == 3
    assert bottleneck_w.shape[0] == bottleneck_w.shape[1]
    assert out_w.shape == (1, down1_w.shape[0], 3, 3)

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    caps = adapter.capabilities()
    assert caps.supported_channels == ("x",)
    assert caps.state_shape == (784,)
    assert caps.native_config_hash == MNIST_FM_CONFIG_HASH
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"


# ---------------------------------------------------------------------------
# 2. Every required engine-side capability flag is True.
# ---------------------------------------------------------------------------


def test_adapter_loads_handshake(mnist_fm_weights_path: Path) -> None:
    """The adapter's capability surface exposes all engine-side flags."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    caps = adapter.capabilities()
    for flag in (
        "has_ode_integration_surface",
        "has_restart_boundary",
        "has_condition_injection",
        "has_trajectory_digest",
        "has_prior_export",
        "has_state_export",
        "has_deterministic_seed",
        "has_materialization_route",
        "has_continuous_channels",
    ):
        assert getattr(caps, flag) is True, f"capability flag {flag!r} is not True"


# ---------------------------------------------------------------------------
# 3. Adapter satisfies the @runtime_checkable Protocol.
# ---------------------------------------------------------------------------


def test_adapter_satisfies_protocol(mnist_fm_weights_path: Path) -> None:
    """The adapter passes ``isinstance(adapter, FlowMatchingODEAdapter)``."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        "MnistFmAdapter does not satisfy FlowMatchingODEAdapter Protocol"
    )


# ---------------------------------------------------------------------------
# 4. Engine.run_round drives an end-to-end round; endpoint finite and in-bounds.
# ---------------------------------------------------------------------------


def test_run_round_produces_target_resembling_samples(
    mnist_fm_weights_path: Path,
) -> None:
    """Drive ``Engine.run_round``; the endpoint is finite and inside ``[-1, 1]^784``."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    from adaptive_reflow.frame import Engine

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    engine = Engine()
    bundle = adapter.build_initial_state(
        batch_id="batch-mnist-3", sample_id="sample-mnist-3"
    )
    policy = _make_final_policy(
        policy_id="policy-mnist-3", run_id="run-mnist-3", beta=0.0
    )
    condition = _make_condition_delta(target_round=0, num_steps=20)
    phase_state = _make_phase_state()

    result = engine.run_round(
        round_index=0,
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition,
        seed=42,
    )

    assert result.round_trace.audit_codes == ()
    assert result.round_trace.detached is True
    endpoint = _endpoint_from_trace(adapter, result.round_trace.integrator_trace)
    assert np.all(np.isfinite(endpoint)), f"endpoint has NaN/Inf: {endpoint!r}"
    assert np.all(np.abs(endpoint) <= 1.0), (
        f"endpoint escapes bounding box [-1, 1]^784; "
        f"max abs = {float(np.max(np.abs(endpoint))):.3f}"
    )


# ---------------------------------------------------------------------------
# 5. Two identical scenarios are byte-identical at every native digest.
# ---------------------------------------------------------------------------


def test_byte_determinism_across_runs(mnist_fm_weights_path: Path) -> None:
    """Run the same 10-round scenario twice from identical seeds."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    from adaptive_reflow.frame import Engine

    def _drive(num_steps: int = 20) -> list[str]:
        adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
        engine = Engine()
        phase_state = _make_phase_state()
        policy = _make_final_policy(
            policy_id="policy-det-mnist",
            run_id="run-det-mnist",
            beta=0.0,
        )
        digests: list[str] = []
        bundle = adapter.build_initial_state(
            batch_id="batch-det-mnist", sample_id="sample-det-mnist"
        )
        for r in range(10):
            condition = _make_condition_delta(target_round=r, num_steps=num_steps)
            result = engine.run_round(
                round_index=r,
                phase_state=phase_state,
                bundle=bundle,
                adapter=adapter,
                policy=policy,
                condition_delta=condition,
                seed=2024,
            )
            digests.append(result.round_trace.integrator_trace.native_state_digest)
            phase_state = result.next_phase_state
            bundle = adapter.observe_endpoint(
                result.round_trace.integrator_trace,
                adapter.build_initial_state(
                    batch_id="batch-det-mnist", sample_id="sample-det-mnist"
                ),
            )
        return digests

    digests_a = _drive()
    digests_b = _drive()
    assert digests_a == digests_b, "native_state_digest drift across runs"


# ---------------------------------------------------------------------------
# 6. solve_ode produces finite endpoints for many seeds.
# ---------------------------------------------------------------------------


def test_no_nan_over_many_seeds(mnist_fm_weights_path: Path) -> None:
    """Loop over ``seed in {0..19}``; assert every endpoint is finite."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    bundle = adapter.build_initial_state(
        batch_id="batch-nan-mnist", sample_id="sample-nan-mnist"
    )
    condition = _make_condition_delta(target_round=0, num_steps=20)

    for seed in range(20):
        trace = adapter.solve_ode(bundle, condition, seed=seed)
        endpoint = _endpoint_from_trace(adapter, trace)
        assert np.all(np.isfinite(endpoint)), f"non-finite endpoint at seed={seed}"


# ---------------------------------------------------------------------------
# 7. observe_endpoint returns a StateBundle resolving to a (784,) array.
# ---------------------------------------------------------------------------


def test_endpoint_shape_correct(mnist_fm_weights_path: Path) -> None:
    """``observe_endpoint`` resolves under the adapter's native-state cache to ``(784,)``."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    bundle = adapter.build_initial_state(
        batch_id="batch-shape", sample_id="sample-shape"
    )
    condition = _make_condition_delta(target_round=0, num_steps=10)
    trace = adapter.solve_ode(bundle, condition, seed=1)
    endpoint_bundle = adapter.observe_endpoint(trace, bundle)
    # Resolve the endpoint digest via the adapter's native-state cache.
    x = adapter._native_states[endpoint_bundle.native_state_digest]["x"]  # noqa: SLF001
    arr = np.asarray(x, dtype=np.float64)
    assert arr.shape == (784,), f"endpoint shape {arr.shape!r} is not (784,)"


# ---------------------------------------------------------------------------
# 8. Protocol surface is intact and non-mutating.
# ---------------------------------------------------------------------------


def test_protocol_surface_intact(mnist_fm_weights_path: Path) -> None:
    """Every documented method is callable; non-mutating methods don't mutate."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    from adaptive_reflow.frame import ODEConditionDelta
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    assert isinstance(adapter, FlowMatchingODEAdapter)
    for name in (
        "capabilities",
        "build_initial_state",
        "export_endpoint",
        "detach_and_validate_endpoint",
        "apply_restart_distribution",
        "compose_condition",
        "solve_ode",
        "observe_endpoint",
    ):
        method = getattr(adapter, name, None)
        assert callable(method), f"method {name!r} is not callable"

    bundle_a = adapter.build_initial_state(
        batch_id="batch-proto-mnist", sample_id="sample-proto-mnist"
    )
    bundle_a_before = _hash_bundle(bundle_a)
    caps_before = adapter.capabilities()
    _ = adapter.capabilities()
    caps_after = adapter.capabilities()
    assert caps_before == caps_after

    after_export = adapter.export_endpoint(bundle_a)
    assert _hash_bundle(after_export) == bundle_a_before
    after_detach = adapter.detach_and_validate_endpoint(bundle_a)
    assert _hash_bundle(after_detach) == bundle_a_before

    delta = ODEConditionDelta(
        delta_spec={"num_steps": 10},
        source="proto-test-mnist",
        target_round=0,
        calibration_artifact_hash="cal-proto-mnist",
    )
    composed = adapter.compose_condition(bundle_a, delta)
    assert composed is not None
    assert _hash_bundle(bundle_a) == bundle_a_before


# ---------------------------------------------------------------------------
# 9. apply_restart_distribution blends with the right memory fraction.
# ---------------------------------------------------------------------------


def test_restart_blend_respects_memory_fraction(mnist_fm_weights_path: Path) -> None:
    """``beta = 0`` keeps prior; ``beta = 1`` draws fresh; ``beta = 0.5`` midpoints."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    bundle = adapter.build_initial_state(
        batch_id="batch-restart-blend-mnist", sample_id="sample-restart-blend-mnist"
    )
    prior_x0 = _native_x0(adapter, bundle.native_state_digest).copy()

    policy_keep = _make_final_policy(
        policy_id="policy-keep-mnist", run_id="run-keep-mnist", beta=0.0
    )
    kept = adapter.apply_restart_distribution(bundle, policy_keep)
    kept_x0 = _native_x0(adapter, kept.native_state_digest)
    assert np.allclose(kept_x0, prior_x0), "beta=0.0 should keep prior verbatim"

    policy_fresh = _make_final_policy(
        policy_id="policy-fresh-mnist", run_id="run-fresh-mnist", beta=1.0
    )
    fresh = adapter.apply_restart_distribution(bundle, policy_fresh)
    fresh_x0_expected = _compute_fresh_x0(policy_fresh, source_round=bundle.source_round)
    fresh_x0_actual = _native_x0(adapter, fresh.native_state_digest)
    assert np.allclose(fresh_x0_actual, fresh_x0_expected)
    assert not np.allclose(fresh_x0_actual, prior_x0), "beta=1.0 must not retain the prior"

    policy_mid = _make_final_policy(
        policy_id="policy-mid-mnist", run_id="run-mid-mnist", beta=0.5
    )
    mid = adapter.apply_restart_distribution(bundle, policy_mid)
    mid_x0 = _native_x0(adapter, mid.native_state_digest)
    expected_mid = 0.5 * prior_x0 + 0.5 * _compute_fresh_x0(
        policy_mid, source_round=bundle.source_round
    )
    assert np.allclose(mid_x0, expected_mid, atol=1e-12)


# ---------------------------------------------------------------------------
# 10. Engine.run_round drives 20 alternating-restart rounds; < 120s budget.
# ---------------------------------------------------------------------------


@pytest.mark.stress
def test_engine_stress_20_rounds_with_restart(mnist_fm_weights_path: Path) -> None:
    """20 rounds alternating restart_beta between ``0.0`` and ``0.5``."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    from adaptive_reflow.frame import Engine

    NUM_ROUNDS = 20
    CPU_BUDGET_SECONDS = 120.0

    def _drive(seed: int):
        adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
        engine = Engine()
        phase_state = _make_phase_state(horizon_remaining=NUM_ROUNDS + 10)
        results = []
        start = time.perf_counter()
        for r in range(NUM_ROUNDS):
            bundle = adapter.build_initial_state(
                batch_id="batch-stress-mnist", sample_id="sample-stress-mnist"
            )
            beta = 0.0 if (r % 2 == 0) else 0.5
            policy = _make_final_policy(
                policy_id=f"policy-stress-mnist-{r}",
                run_id="run-stress-mnist",
                beta=beta,
                target_round=r,
            )
            condition = _make_condition_delta(target_round=r, num_steps=10)
            result = engine.run_round(
                round_index=r,
                phase_state=phase_state,
                bundle=bundle,
                adapter=adapter,
                policy=policy,
                condition_delta=condition,
                seed=seed,
            )
            results.append(result)
            phase_state = result.next_phase_state
        elapsed = time.perf_counter() - start
        return results, elapsed

    results, elapsed = _drive(seed=7)
    assert elapsed < CPU_BUDGET_SECONDS, f"stress run took {elapsed:.2f}s; budget {CPU_BUDGET_SECONDS}s"
    assert len(results) == NUM_ROUNDS
    for r, result in enumerate(results):
        ok, errs = validate_round_trace(result.round_trace)
        assert ok, f"round {r} failed validation: {errs!r}"


# ---------------------------------------------------------------------------
# 11. inject_forward_noise adds the perturbation and stamps provenance.
# ---------------------------------------------------------------------------


def test_inject_forward_noise_hook(mnist_fm_weights_path: Path) -> None:
    """``inject_forward_noise`` adds the perturbation and stamps ``forward_noise_applied``."""
    from adaptive_reflow.adapters.mnist_fm import (
        AUDIT_MNIST_FM_FORWARD_NOISE_APPLIED,
        MnistFmAdapter,
    )

    adapter = MnistFmAdapter(weights_path=mnist_fm_weights_path)
    bundle = adapter.build_initial_state(
        batch_id="batch-noise-mnist", sample_id="sample-noise-mnist"
    )
    prior_x0 = _native_x0(adapter, bundle.native_state_digest).copy()
    injected = np.full((784,), 0.05, dtype=np.float64)
    new_bundle = adapter.inject_forward_noise(bundle, injected)
    assert AUDIT_MNIST_FM_FORWARD_NOISE_APPLIED in new_bundle.provenance
    new_x0 = _native_x0(adapter, new_bundle.native_state_digest)
    assert np.allclose(new_x0, np.clip(prior_x0 + injected, -1.0, 1.0), atol=1e-12)
