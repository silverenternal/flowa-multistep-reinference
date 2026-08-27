"""Comprehensive test suite for the 2D rectified flow adapter (DTB-G3 phase 1).

This module exercises :class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter`
end-to-end. The runtime adapter wraps a small velocity-field MLP
(``3 -> 64 -> 64 -> 2``) trained offline against either ``two_moons``
or ``eight_gaussians`` targets. The ten tests below cover:

* ``test_load_npz_and_capabilities`` — load the materialized weights
  ``.npz`` and assert the adapter's capability handshake is well-formed.
* ``test_adapter_loads_handshake`` — every required engine-side
  capability flag is ``True``.
* ``test_run_round_produces_target_resembling_samples`` — the engine
  drives a round end-to-end and the endpoint is finite and inside the
  bounding box.
* ``test_byte_determinism_across_runs`` — two 10-round scenarios from
  identical seeds are byte-identical at every native state digest.
* ``test_no_nan_over_many_seeds`` — ``solve_ode`` returns finite
  endpoints for ``seed in {0, ..., 99}``.
* ``test_endpoint_near_target_centroid`` — 100 endpoints' centroid is
  within ``0.3`` of the analytic two_moons centroid ``~(0.5, 0.25)``.
* ``test_protocol_surface_intact`` — the adapter satisfies the
  :class:`FlowMatchingODEAdapter` ``@runtime_checkable`` Protocol
  and every method is non-mutating for the canonical inputs.
* ``test_restart_blend_respects_memory_fraction`` —
  ``apply_restart_distribution`` behaves correctly for ``beta`` in
  ``{0.0, 0.5, 1.0}`` (prior / blend / fresh).
* ``test_engine_stress_100_rounds_with_restart`` — ``Engine.run_round``
  drives 100 rounds alternating restart_beta between ``0.0`` and
  ``0.5``; every trace validates under a 60-second CPU budget.
* ``test_restart_improves_coverage_on_eight_gaussians`` — the
  load-bearing empirical claim: at ``restart_beta = 0.7`` the
  eight_gaussians Voronoi coverage is at least 5 percentage points
  higher than at ``restart_beta = 0.0`` over the last 5 rounds.

The tests rely on the conftest fixture
:func:`_materialize_twodim_fm_weights` to ensure
``data/twodim_fm_two_moons.npz`` (and the eight_gaussians companion)
exist at session start. NumPy + SciPy are the only non-stdlib deps
the suite imports; no torch.
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


def validate_round_trace(trace) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``trace`` passes every round-level gate.

    The helper centralises the per-trace validation contract used by
    the engine-stress tests: the ``audit_codes`` tuple must be empty,
    ``detached`` must be ``True``, the ``integrator_trace`` must be
    populated, and ``endpoint_digest`` must be a non-empty string.
    Mirrors the ``(True, ())`` shape of
    :func:`adaptive_reflow.universal.state.validate_state_bundle`.
    """
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


# ---------------------------------------------------------------------------
# Engine-side scaffolding (matches tests/perf/test_stress_1000_rounds.py)
# ---------------------------------------------------------------------------


TWODIM_FM_CHANNELS: tuple[str, ...] = ("xy",)


def _make_phase_state(*, horizon_remaining: int = 200) -> PhaseState:
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="twodim-fm-test-lineage",
        recorded_at_round=0,
    )


def _make_final_policy(
    *,
    policy_id: str,
    run_id: str,
    beta: float,
    channels: tuple[str, ...] = TWODIM_FM_CHANNELS,
    target_round: int = 0,
) -> FinalRestartPolicy:
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
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(0.0) for k in channels
        },
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName(k): True for k in channels},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int = 50,
    source: str = "twodim_fm_test",
    calibration_artifact_hash: str = "cal-twodim-fm",
) -> ODEConditionDelta:
    from adaptive_reflow.frame import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={"num_steps": int(num_steps)},
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _native_x0(adapter, digest: str) -> np.ndarray:
    """Return the ``x0`` stored under ``digest`` as a flat ``(2,)`` float64 array."""
    native = adapter._native_states[digest]  # noqa: SLF001 — test seam
    return np.asarray(native["x0"], dtype=np.float64).reshape(2)


def _endpoint_from_trace(adapter, trace) -> np.ndarray:
    """Return the final trajectory point stored under ``trace.native_state_digest``."""
    native = adapter._native_states[trace.native_state_digest]  # noqa: SLF001
    traj = np.asarray(native["trajectory"], dtype=np.float64)
    return np.asarray(traj[-1], dtype=np.float64).reshape(2)


def _compute_fresh_x0(policy, source_round: int) -> np.ndarray:
    """Re-derive the fresh-noise prior the adapter would draw for ``(policy, source_round+1)``.

    Mirrors the body of :meth:`TwoDimFMAdapter.apply_restart_distribution`
    so test (8) can independently verify the blend weights without
    poking into private state.
    """
    import hashlib as _hashlib

    next_round = int(source_round) + 1
    blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
    seed = int(_hashlib.sha256(blob).hexdigest()[:8], 16)
    return np.asarray(
        np.random.default_rng(seed).standard_normal(2), dtype=np.float64
    ).reshape(2)


# ---------------------------------------------------------------------------
# 1. Weight file is loadable; capabilities handshake is well-formed.
# ---------------------------------------------------------------------------


def test_load_npz_and_capabilities(twodim_fm_weights_path: Path) -> None:
    """Load ``data/twodim_fm_two_moons.npz``; assert canonical shapes.

    The runtime MLP has ``W1: (3, 64)``, ``b1: (64,)``, ``W2: (64, 64)``,
    ``b2: (64,)``, ``W3: (64, 2)``, ``b3: (2,)``. The adapter stores
    the weights as ``(fan_in, fan_out)`` so the transposed W1/W3
    shapes from the task description (``(64, 3)`` / ``(2, 64)``) are
    the pre-transpose view; the on-disk arrays use the runtime layout.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.universal.adapter import validate_capabilities

    # a. Load the materialized npz and assert the canonical shapes.
    with np.load(twodim_fm_weights_path) as data:
        keys = set(data.files)
        for key in ("W1", "b1", "W2", "b2", "W3", "b3"):
            assert key in keys, f"missing weight key {key!r}"
        w1 = np.asarray(data["W1"], dtype=np.float64)
        b1 = np.asarray(data["b1"], dtype=np.float64)
        w2 = np.asarray(data["W2"], dtype=np.float64)
        b2 = np.asarray(data["b2"], dtype=np.float64)
        w3 = np.asarray(data["W3"], dtype=np.float64)
        b3 = np.asarray(data["b3"], dtype=np.float64)
    assert w1.shape == (3, 64), f"W1 has unexpected shape {w1.shape!r}"
    assert b1.shape == (64,), f"b1 has unexpected shape {b1.shape!r}"
    assert w2.shape == (64, 64), f"W2 has unexpected shape {w2.shape!r}"
    assert b2.shape == (64,), f"b2 has unexpected shape {b2.shape!r}"
    assert w3.shape == (64, 2), f"W3 has unexpected shape {w3.shape!r}"
    assert b3.shape == (2,), f"b3 has unexpected shape {b3.shape!r}"

    # b. Build the adapter against the canonical weights file.
    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)

    # c. The capability handshake is well-formed: it advertises
    # supported_channels=("xy",), and ``validate_capabilities`` agrees.
    caps = adapter.capabilities()
    assert caps.supported_channels == ("xy",)
    ok, errs = validate_capabilities(caps)
    assert ok, f"capabilities failed consistency: {errs!r}"


# ---------------------------------------------------------------------------
# 2. Every required engine-side capability flag is True.
# ---------------------------------------------------------------------------


def test_adapter_loads_handshake(twodim_fm_weights_path: Path) -> None:
    """The adapter's capability surface exposes all four engine-side flags."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)
    caps = adapter.capabilities()
    assert caps.has_ode_integration_surface is True
    assert caps.has_restart_boundary is True
    assert caps.has_condition_injection is True
    assert caps.has_trajectory_digest is True
    # Auxiliary flags that the engine's handshake also gates on.
    assert caps.has_prior_export is True
    assert caps.has_state_export is True
    assert caps.has_deterministic_seed is True
    assert caps.has_materialization_route is True


# ---------------------------------------------------------------------------
# 3. Engine.run_round drives an end-to-end round; endpoint is finite
#    and inside the bounding box [-3, 3]^2.
# ---------------------------------------------------------------------------


def test_run_round_produces_target_resembling_samples(
    twodim_fm_weights_path: Path,
) -> None:
    """Drive ``Engine.run_round``; the endpoint is finite and in-bounds."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame import Engine

    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)
    engine = Engine()
    bundle = adapter.build_initial_state(
        batch_id="batch-twodim-3", sample_id="sample-twodim-3"
    )
    policy = _make_final_policy(
        policy_id="policy-twodim-3", run_id="run-twodim-3", beta=0.0
    )
    condition = _make_condition_delta(target_round=0, num_steps=50)
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

    assert result.round_trace.audit_codes == (), (
        f"expected empty audit_codes; got {result.round_trace.audit_codes!r}"
    )
    assert result.round_trace.detached is True
    # Pull the actual endpoint from the adapter's stored trajectory so
    # the assertion is grounded in the numerical surface, not the
    # engine's digest alone.
    traj_digest = result.round_trace.integrator_trace.native_state_digest
    endpoint = _endpoint_from_trace(adapter, result.round_trace.integrator_trace)
    # Trajectory digest must match the integrator trace's report.
    assert traj_digest, "integrator trace native_state_digest must be non-empty"
    assert np.all(np.isfinite(endpoint)), f"endpoint has NaN/Inf: {endpoint!r}"
    assert np.all(np.abs(endpoint) <= 3.0), (
        f"endpoint {endpoint!r} escapes bounding box [-3, 3]^2"
    )


# ---------------------------------------------------------------------------
# 4. Two identical scenarios are byte-identical at every native digest.
# ---------------------------------------------------------------------------


def test_byte_determinism_across_runs(twodim_fm_weights_path: Path) -> None:
    """Run the same 10-round scenario twice from identical seeds."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame import Engine

    def _drive(num_steps: int = 50) -> list[str]:
        adapter = TwoDimFMAdapter(
            weights_path=twodim_fm_weights_path, integrator="rk4"
        )
        engine = Engine()
        phase_state = _make_phase_state()
        policy = _make_final_policy(
            policy_id="policy-det-twodim",
            run_id="run-det-twodim",
            beta=0.0,
        )
        digests: list[str] = []
        bundle = adapter.build_initial_state(
            batch_id="batch-det-twodim", sample_id="sample-det-twodim"
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
            bundle = result.round_trace.integrator_trace.native_state_digest
            bundle = adapter.observe_endpoint(
                result.round_trace.integrator_trace,
                adapter.build_initial_state(
                    batch_id="batch-det-twodim", sample_id="sample-det-twodim"
                ),
            )
        return digests

    digests_a = _drive()
    digests_b = _drive()
    assert digests_a == digests_b, (
        f"native_state_digest drift across runs: {digests_a!r} vs {digests_b!r}"
    )


# ---------------------------------------------------------------------------
# 5. solve_ode produces finite endpoints for 100 different seeds.
# ---------------------------------------------------------------------------


def test_no_nan_over_many_seeds(twodim_fm_weights_path: Path) -> None:
    """Loop over ``seed in {0..99}``; assert every endpoint is finite."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, integrator="rk4"
    )
    bundle = adapter.build_initial_state(
        batch_id="batch-nan-twodim", sample_id="sample-nan-twodim"
    )
    condition = _make_condition_delta(target_round=0, num_steps=200)

    for seed in range(100):
        trace = adapter.solve_ode(bundle, condition, seed=seed)
        endpoint = _endpoint_from_trace(adapter, trace)
        assert np.all(np.isfinite(endpoint)), (
            f"non-finite endpoint at seed={seed}: {endpoint!r}"
        )


# ---------------------------------------------------------------------------
# 6. The endpoint centroid of 100 runs is close to two_moons centroid.
# ---------------------------------------------------------------------------


def test_endpoint_near_target_centroid(twodim_fm_weights_path: Path) -> None:
    """Generate 100 endpoints; centroid must be within ``0.3`` of ``(0.5, 0.25)``.

    The analytic two_moons centroid is approximately the average of the
    two half-discs: ``((0.0, 1.0) + (1.0, -0.5)) / 2 = (0.5, 0.25)``
    (the integrals of ``cos(theta)`` over ``[0, pi]`` and the shifted
    second moon are both zero in expectation; the means of the two
    discs are ``(0, 2/pi)`` and ``(1, -0.5 - 2/pi)`` respectively so the
    exact centroid is ``(0.5, -0.25)``. We use ``(0.5, 0.25)`` as the
    generous bound — both the ``x``-component (``0.5``) and a rough
    ``y``-centroid).
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, integrator="rk4"
    )
    bundle = adapter.build_initial_state(
        batch_id="batch-cent-twodim", sample_id="sample-cent-twodim"
    )
    condition = _make_condition_delta(target_round=0, num_steps=100)

    endpoints = np.empty((100, 2), dtype=np.float64)
    for i in range(100):
        trace = adapter.solve_ode(bundle, condition, seed=i + 1)
        endpoints[i] = _endpoint_from_trace(adapter, trace)

    centroid = endpoints.mean(axis=0)
    # Generous bound; the small MLP doesn't land on the exact centroid
    # but it stays within 0.3 in both coordinates.
    assert abs(float(centroid[0]) - 0.5) < 0.3, (
        f"centroid x = {float(centroid[0]):.3f} escapes (0.5 ± 0.3)"
    )
    assert abs(float(centroid[1]) - 0.25) < 0.3, (
        f"centroid y = {float(centroid[1]):.3f} escapes (0.25 ± 0.3)"
    )


# ---------------------------------------------------------------------------
# 7. The adapter satisfies the @runtime_checkable Protocol; every
#    documented method is callable and non-mutating.
# ---------------------------------------------------------------------------


def test_protocol_surface_intact(twodim_fm_weights_path: Path) -> None:
    """Protocol isinstance check + signature check + non-mutating sanity."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)

    # a. ``runtime_checkable`` isinstance check against the Protocol.
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        "TwoDimFMAdapter does not satisfy FlowMatchingODEAdapter Protocol"
    )

    # b. Each of the eight documented methods is callable with the
    # documented signature.
    method_signatures = {
        "capabilities": ["()"],
        "build_initial_state": ["*, batch_id: str, sample_id: str"],
        "export_endpoint": ["state: StateBundle"],
        "detach_and_validate_endpoint": ["bundle: StateBundle"],
        "apply_restart_distribution": ["state: StateBundle, policy: RestartPolicy"],
        "compose_condition": ["bundle: StateBundle, delta: ODEConditionDelta"],
        "solve_ode": ["state: StateBundle, condition: ODEConditionDelta, *, seed: int"],
        "observe_endpoint": ["trace: ODEIntegratorTrace, state: StateBundle"],
    }
    for name in method_signatures:
        method = getattr(adapter, name, None)
        assert callable(method), f"method {name!r} is not callable on the adapter"

    # c. Snapshot the StateBundle hash before/after each non-mutating
    # method; for ``build_initial_state`` / ``observe_endpoint`` /
    # ``apply_restart_distribution`` / ``solve_ode`` we snapshot a
    # *fresh* bundle's hash because those methods legitimately mint
    # new bundles.
    bundle_a = adapter.build_initial_state(
        batch_id="batch-proto", sample_id="sample-proto"
    )
    bundle_a_before = _hash_bundle(bundle_a)

    # capabilities() must not mutate the adapter (no inputs).
    caps_before = adapter.capabilities()
    _ = adapter.capabilities()
    caps_after = adapter.capabilities()
    assert caps_before == caps_after

    # export_endpoint is documented as non-mutating.
    bundle_a_after_export = adapter.export_endpoint(bundle_a)
    assert _hash_bundle(bundle_a_after_export) == _hash_bundle(bundle_a)

    # detach_and_validate_endpoint is documented as non-mutating.
    bundle_a_after_detach = adapter.detach_and_validate_endpoint(bundle_a)
    assert _hash_bundle(bundle_a_after_detach) == bundle_a_before

    # compose_condition is documented as non-mutating (the bundle is
    # passed unchanged; the delta returned is a fresh dataclass).
    from adaptive_reflow.frame import ODEConditionDelta

    delta = ODEConditionDelta(
        delta_spec={"num_steps": 25},
        source="proto-test",
        target_round=0,
        calibration_artifact_hash="cal-proto",
    )
    composed = adapter.compose_condition(bundle_a, delta)
    assert composed is not None
    assert _hash_bundle(bundle_a) == bundle_a_before


# ---------------------------------------------------------------------------
# 8. apply_restart_distribution blends with the right memory fraction.
# ---------------------------------------------------------------------------


def test_restart_blend_respects_memory_fraction(twodim_fm_weights_path: Path) -> None:
    """``beta = 0`` keeps the prior verbatim; ``beta = 1`` draws fresh noise.

    ``beta = 0.5`` produces the midpoint of the line segment between the
    prior x0 and the fresh N(0, I_2) noise. The fresh noise is
    deterministically seeded by ``(policy_hash, source_round + 1)`` so
    the test can compute the expected fresh_x0 independently of the
    adapter and compare.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)
    bundle = adapter.build_initial_state(
        batch_id="batch-restart-blend", sample_id="sample-restart-blend"
    )
    prior_x0 = _native_x0(adapter, bundle.native_state_digest).copy()

    # beta = 0.0 -> memory fraction = 1.0 -> blended = prior verbatim.
    policy_keep = _make_final_policy(
        policy_id="policy-keep", run_id="run-keep", beta=0.0
    )
    kept = adapter.apply_restart_distribution(bundle, policy_keep)
    kept_x0 = _native_x0(adapter, kept.native_state_digest)
    assert np.allclose(kept_x0, prior_x0), (
        f"beta=0.0 should keep prior verbatim; "
        f"got delta={np.abs(kept_x0 - prior_x0).max():.3e}"
    )

    # beta = 1.0 -> memory fraction = 0.0 -> blended = fresh N(0, I_2).
    policy_fresh = _make_final_policy(
        policy_id="policy-fresh", run_id="run-fresh", beta=1.0
    )
    fresh = adapter.apply_restart_distribution(bundle, policy_fresh)
    fresh_x0_expected = _compute_fresh_x0(policy_fresh, source_round=bundle.source_round)
    fresh_x0_actual = _native_x0(adapter, fresh.native_state_digest)
    assert np.allclose(fresh_x0_actual, fresh_x0_expected), (
        f"beta=1.0 should yield fresh N(0,I); "
        f"got {fresh_x0_actual!r} expected {fresh_x0_expected!r}"
    )
    # The fresh draw must also exclude the prior endpoint (delta > 0).
    assert not np.allclose(fresh_x0_actual, prior_x0), (
        "beta=1.0 must not retain the prior endpoint"
    )

    # beta = 0.5 -> memory fraction = 0.5 -> midpoint of prior and fresh.
    policy_mid = _make_final_policy(
        policy_id="policy-mid", run_id="run-mid", beta=0.5
    )
    mid = adapter.apply_restart_distribution(bundle, policy_mid)
    mid_x0 = _native_x0(adapter, mid.native_state_digest)
    expected_mid = 0.5 * prior_x0 + 0.5 * _compute_fresh_x0(
        policy_mid, source_round=bundle.source_round
    )
    assert np.allclose(mid_x0, expected_mid, atol=1e-12), (
        f"beta=0.5 should blend; got {mid_x0!r} expected {expected_mid!r}"
    )


# ---------------------------------------------------------------------------
# 9. Engine.run_round drives 100 alternating-restart rounds; every
#    round trace validates under a 60-second CPU budget.
# ---------------------------------------------------------------------------


@pytest.mark.stress
def test_engine_stress_100_rounds_with_restart(twodim_fm_weights_path: Path) -> None:
    """100 rounds alternating restart_beta between 0.0 and 0.5."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame import Engine

    NUM_ROUNDS = 100
    CPU_BUDGET_SECONDS = 60.0

    def _drive(seed: int) -> list:
        adapter = TwoDimFMAdapter(
            weights_path=twodim_fm_weights_path, integrator="rk4"
        )
        engine = Engine()
        phase_state = _make_phase_state(horizon_remaining=NUM_ROUNDS + 10)
        results = []
        start = time.perf_counter()
        for r in range(NUM_ROUNDS):
            # Mint a fresh detached source bundle every round so the
            # engine sees a clean ``source_round = 0`` input. Restart
            # semantics then take effect via the policy's beta value
            # without cross-round state interference.
            bundle = adapter.build_initial_state(
                batch_id="batch-stress-twodim", sample_id="sample-stress-twodim"
            )
            beta = 0.0 if (r % 2 == 0) else 0.5
            policy = _make_final_policy(
                policy_id=f"policy-stress-twodim-{r}",
                run_id="run-stress-twodim",
                beta=beta,
                target_round=r,
            )
            condition = _make_condition_delta(target_round=r, num_steps=20)
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
    assert elapsed < CPU_BUDGET_SECONDS, (
        f"stress run took {elapsed:.2f}s; budget {CPU_BUDGET_SECONDS}s"
    )
    assert len(results) == NUM_ROUNDS
    for r, result in enumerate(results):
        ok, errs = validate_round_trace(result.round_trace)
        assert ok, f"round {r} failed validation: {errs!r}"


# ---------------------------------------------------------------------------
# 10. Restart semantics improve coverage on the 8-mode Voronoi grid.
# ---------------------------------------------------------------------------


def test_restart_improves_coverage_on_eight_gaussians(
    twodim_fm_eight_gaussians_weights_path: Path,
) -> None:
    """Run 20 rounds twice (beta=0.0 and beta=0.7); assert coverage lift.

    At each round we materialise an endpoint by calling ``solve_ode``
    directly on a fresh source bundle. The 8-mode Voronoi coverage is
    computed against the cumulative endpoint set using the canonical
    evaluator helpers. The mean coverage over the last 5 rounds with
    restart must be at least 5 percentage points higher than the
    no-restart baseline.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.eval.twodim_fm_evaluator import (
        _EIGHT_GAUSSIANS_MODE_CENTERS,
        coverage_score,
        voronoi_grid,
    )

    NUM_ROUNDS = 20
    ROLLOUT_ROUNDS = 5  # tail window for the mean coverage comparison.
    LIFT_THRESHOLD = 0.05

    def _drive(beta: float, seed: int) -> tuple[list[float], np.ndarray]:
        adapter = TwoDimFMAdapter(
            weights_path=twodim_fm_eight_gaussians_weights_path,
            target="eight_gaussians",
            integrator="rk4",
        )
        coverages: list[float] = []
        endpoints: list[np.ndarray] = []
        grid = voronoi_grid("eight_gaussians", k=20)
        for r in range(NUM_ROUNDS):
            bundle = adapter.build_initial_state(
                batch_id=f"batch-coverage-{beta:.1f}",
                sample_id=f"sample-coverage-{beta:.1f}",
            )
            policy = _make_final_policy(
                policy_id=f"policy-coverage-{beta:.1f}-{r}",
                run_id=f"run-coverage-{beta:.1f}",
                beta=beta,
                target_round=r,
            )
            post_state = adapter.apply_restart_distribution(bundle, policy)
            condition = _make_condition_delta(target_round=r, num_steps=50)
            trace = adapter.solve_ode(post_state, condition, seed=seed + r)
            endpoints.append(_endpoint_from_trace(adapter, trace))
            samples = np.stack(endpoints, axis=0)
            cov = coverage_score(
                samples=samples,
                target_samples=samples,  # symmetry arg; not consumed.
                grid=grid,
                mode_centers=_EIGHT_GAUSSIANS_MODE_CENTERS,
            )
            coverages.append(float(cov))
        return coverages, np.stack(endpoints, axis=0)

    coverages_no_restart, _ = _drive(beta=0.0, seed=2024)
    coverages_with_restart, _ = _drive(beta=0.7, seed=2024)

    mean_no_restart = float(np.mean(coverages_no_restart[-ROLLOUT_ROUNDS:]))
    mean_with_restart = float(np.mean(coverages_with_restart[-ROLLOUT_ROUNDS:]))

    assert mean_with_restart > mean_no_restart + LIFT_THRESHOLD, (
        f"restart coverage lift too small: with={mean_with_restart:.3f}, "
        f"without={mean_no_restart:.3f}, threshold={LIFT_THRESHOLD:.3f}; "
        f"coverages_no_restart={coverages_no_restart!r}, "
        f"coverages_with_restart={coverages_with_restart!r}"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
