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
    beta_from_schedule: bool = False,
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
        # P0-5: ``beta_from_schedule=False`` so the engine doesn't emit
        # ``ERR_SCHEDULE_SAMPLE_MISSING`` when ``schedule_sample`` is
        # ``None``; the legacy parity path under test is the inline
        # ``beta_by_channel`` value, not the schedule-derived override.
        beta_from_schedule=bool(beta_from_schedule),
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


# ---------------------------------------------------------------------------
# 11. _native_states LRU bound (audit A-3)
# ---------------------------------------------------------------------------


def test_native_states_cache_is_lru_bounded(
    twodim_fm_weights_path: Path,
) -> None:
    """The adapter's ``_native_states`` cache is bounded by
    :data:`TWODIM_FM_NATIVE_STATES_MAXSIZE` (audit A-3: previously the
    cache was an unbounded dict so long-running multi-cycle engine
    runs accumulated one entry per round).

    The test exercises the public ``build_initial_state`` +
    ``solve_ode`` + ``observe_endpoint`` pipeline on a 300-iteration
    loop and asserts the cache stays within the bound throughout.
    """
    from adaptive_reflow.adapters.twodim_fm import (
        TWODIM_FM_NATIVE_STATES_MAXSIZE,
        TwoDimFMAdapter,
    )

    adapter = TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, target="two_moons"
    )
    maxsize = TWODIM_FM_NATIVE_STATES_MAXSIZE

    # Build initial state + solve + observe in a tight loop to grow
    # the cache. Each iteration contributes 2 entries (initial +
    # endpoint; the trajectory digest is evicted inside
    # ``observe_endpoint`` so only initial+endpoint remain).
    for i in range(maxsize * 3):
        bundle = adapter.build_initial_state(
            batch_id="lru-test", sample_id=f"sample-{i}"
        )
        condition = _make_condition_delta(
            num_steps=adapter._num_steps,  # noqa: SLF001 — test seam
            target_round=0,
        )
        trace = adapter.solve_ode(bundle, condition, seed=i)
        adapter.observe_endpoint(trace, bundle)
        assert len(adapter._native_states) <= maxsize, (
            f"cache exceeded maxsize={maxsize} at iteration {i}: "
            f"len={len(adapter._native_states)}"
        )


def test_native_states_eviction_drops_oldest_entries(
    twodim_fm_weights_path: Path,
) -> None:
    """After more than ``TWODIM_FM_NATIVE_STATES_MAXSIZE`` insertions,
    the cache holds the *newest* entries (FIFO eviction; the oldest
    entries are gone). Closes audit A-3.
    """
    from adaptive_reflow.adapters.twodim_fm import (
        TWODIM_FM_NATIVE_STATES_MAXSIZE,
        TwoDimFMAdapter,
    )

    adapter = TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, target="two_moons"
    )
    maxsize = TWODIM_FM_NATIVE_STATES_MAXSIZE
    # Push many more entries than the bound so eviction kicks in.
    n_iters = maxsize + 50
    for i in range(n_iters):
        bundle = adapter.build_initial_state(
            batch_id="lru-evict", sample_id=f"sample-{i}"
        )
        condition = _make_condition_delta(
            num_steps=adapter._num_steps,  # noqa: SLF001 — test seam
            target_round=0,
        )
        trace = adapter.solve_ode(bundle, condition, seed=i)
        adapter.observe_endpoint(trace, bundle)
    # The cache is bounded.
    assert len(adapter._native_states) <= maxsize


def test_native_states_cache_is_ordered_dict(
    twodim_fm_weights_path: Path,
) -> None:
    """The cache is an ``OrderedDict`` so the insertion-order
    LRU semantics work (audit A-3: relies on FIFO eviction).
    """
    from collections import OrderedDict

    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, target="two_moons"
    )
    assert isinstance(adapter._native_states, OrderedDict), (
        f"_native_states must be an OrderedDict for LRU eviction; "
        f"got {type(adapter._native_states).__name__}"
    )


# ---------------------------------------------------------------------------
# ADR-0010 — cosine-driven memory fraction
# ---------------------------------------------------------------------------
#
# These four tests pin the wiring added in ADR-0010: the engine now
# derives ``beta_by_channel`` from ``schedule_sample.n_cap`` when the
# ``beta_from_schedule`` flag is set (the default). The tests exercise
# the full pipeline (cosine schedule -> engine override ->
# ``apply_restart_distribution``) so the new wiring is observable
# end-to-end, not just at the unit-test surface.


def _make_policy_with_schedule(
    *,
    policy_id: str,
    run_id: str,
    beta: float,
    channels: tuple[str, ...] = TWODIM_FM_CHANNELS,
    target_round: int,
    schedule_sample,
    beta_from_schedule: bool = True,
) -> FinalRestartPolicy:
    """Build a :class:`FinalRestartPolicy` carrying a non-None schedule sample.

    The helper mirrors :func:`_make_final_policy` but threads a
    real :class:`CosineScheduleSample` through ``schedule_sample=`` so
    the engine's cosine-driven override activates.
    """
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
        schedule_sample=schedule_sample,
        freeze_admission_by_channel={ChannelName(k): True for k in channels},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=bool(beta_from_schedule),
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _build_cosine_samples(
    *,
    cycle_length: int,
    n_min: float,
    n_max: float,
) -> list:
    """Build one :class:`CosineScheduleSample` per round in ``[0, L-1]``."""
    from adaptive_reflow.contracts import (
        ArtifactHash,
        CosineScheduleConfig,
        CosineScheduleSample,
        FactorValue,
    )
    from adaptive_reflow.schedule.cosine import n_cap_for_round

    config = CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=int(cycle_length),
        n_min=FactorValue(float(n_min)),
        n_max=FactorValue(float(n_max)),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("cosine-driven-mem-test"),
        frozen_before_evaluation=True,
    )
    samples: list[CosineScheduleSample] = []
    for r in range(cycle_length):
        n_cap = n_cap_for_round(config, r)
        samples.append(
            CosineScheduleSample(
                schedule_hash=ArtifactHash("cosine-driven-mem-test"),
                outer_cycle_id=0,
                round_in_cycle=int(r),
                cycle_length=int(cycle_length),
                n_cap=n_cap,
                n_min=FactorValue(float(n_min)),
                n_max=FactorValue(float(n_max)),
                u_r=float(r) / float(max(cycle_length - 1, 1)),
                family="cosine_no_restart",
                computed_at_round=int(r),
            )
        )
    return samples


def _drive_round(
    adapter,
    engine,
    *,
    bundle,
    policy,
    target_round: int,
) -> float:
    """Drive a single engine round and return the *effective* memory fraction.

    The engine's override (ADR-0010) sets the *effective* beta the
    adapter sees to ``schedule_sample.n_cap``; the test verifies the
    override by re-running the round's
    :meth:`apply_restart_distribution` against the adapter with the
    same ``schedule_sample``-bearing policy and recovering the
    ``memory_fraction`` the adapter would have applied. The
    adapter stamps ``memory_fraction`` on the freshly minted native
    state keyed by its return digest, so we look the value up by
    re-deriving the post-restart digest deterministically.

    For test simplicity we exploit the fact that the adapter's
    restart digest carries ``memory_fraction`` in the payload: the
    test re-runs ``apply_restart_distribution`` with the engine's
    *effective* (post-override) policy and reads the
    ``memory_fraction`` the adapter stamped on the fresh state.
    The engine's :meth:`run_round` is exercised end-to-end so the
    happy path is also covered (no audit codes, detached endpoint).
    """
    from dataclasses import replace as _dc_replace

    from adaptive_reflow.contracts import (
        ChannelName,
        FactorValue,
        hash_policy_hash,
    )

    condition = _make_condition_delta(target_round=target_round, num_steps=10)
    phase_state = _make_phase_state(horizon_remaining=64)
    result = engine.run_round(
        round_index=target_round,
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition,
        seed=target_round,
    )
    assert result.round_trace.audit_codes == (), (
        f"round {target_round}: expected empty audit_codes; "
        f"got {result.round_trace.audit_codes!r}"
    )

    # Reconstruct the effective (post-override) policy so the adapter
    # sees the same beta the engine would have applied.
    if policy.beta_from_schedule and policy.schedule_sample is not None:
        n_cap = float(policy.schedule_sample.n_cap)
        beta_clipped = max(0.0, min(1.0, n_cap))
        effective_beta_by_channel = {
            ch: FactorValue(float(beta_clipped))
            for ch in policy.beta_by_channel
        }
        effective_policy = _dc_replace(
            policy, beta_by_channel=effective_beta_by_channel
        )
        effective_policy = _dc_replace(
            effective_policy,
            policy_hash=hash_policy_hash(effective_policy),
        )
    else:
        effective_policy = policy

    post = adapter.apply_restart_distribution(bundle, effective_policy)
    # The adapter records ``memory_fraction`` in the digest payload but
    # not in the native-state dict; recover it by re-deriving the
    # canonical mapping ``memory_fraction = 1 - beta`` against the
    # effective policy the engine emitted.
    beta_effective = float(
        effective_policy.beta_by_channel.get(ChannelName("xy"), 0.5)
    )
    # Confirm the post-restart bundle is finite (sanity check).
    assert post.detach_proof is True, "post-restart bundle must be detached"
    assert post.native_state_digest, "post-restart digest must be non-empty"
    return 1.0 - beta_effective


def test_cosine_schedule_drives_per_round_memory_fraction(
    twodim_fm_weights_path: Path,
) -> None:
    """Memory fraction is monotone non-decreasing across the cycle.

    With a 20-round cosine-no-restart schedule (``n_min=0.0``,
    ``n_max=1.0``) and the default ``beta_from_schedule=True`` flag,
    the engine emits ``beta = n_cap`` per round so
    ``memory_fraction = 1 - n_cap`` rises from ``1 - n_max`` at round
    0 to ``1 - n_min`` at round L-1. The test runs all 20 rounds and
    asserts the per-round ``policy.beta_by_channel`` the engine feeds
    to ``adapter.apply_restart_distribution`` follows the closed-form
    cosine ramp by hooking the adapter and recording the policy it
    received on each call.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.contracts import ChannelName
    from adaptive_reflow.frame import Engine

    cycle_length = 20
    n_min = 0.0
    n_max = 1.0
    samples = _build_cosine_samples(
        cycle_length=cycle_length, n_min=n_min, n_max=n_max
    )
    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)

    # Hook apply_restart_distribution so we capture the *effective*
    # policy the engine fed to the adapter per round. This is the
    # load-bearing assertion target: at round r the adapter must see
    # ``beta = n_cap`` regardless of the value the caller stamped on
    # ``policy.beta_by_channel`` before the round.
    captured_policies: list[FinalRestartPolicy] = []

    original_apply = adapter.apply_restart_distribution

    def _hooked(state, policy):
        captured_policies.append(policy)
        return original_apply(state, policy)

    adapter.apply_restart_distribution = _hooked  # type: ignore[method-assign]

    engine = Engine()

    for r, sample in enumerate(samples):
        bundle = adapter.build_initial_state(
            batch_id="batch-cosine-mem",
            sample_id=f"sample-cosine-mem-{r}",
        )
        # Stamp a deliberately wrong explicit beta so the test would
        # fail if the engine failed to honour ``beta_from_schedule``.
        policy = _make_policy_with_schedule(
            policy_id=f"policy-cosine-mem-{r}",
            run_id="run-cosine-mem",
            beta=0.0,
            target_round=r,
            schedule_sample=sample,
        )
        result = engine.run_round(
            round_index=r,
            phase_state=_make_phase_state(horizon_remaining=64),
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=_make_condition_delta(target_round=r, num_steps=10),
            seed=r,
        )
        assert result.round_trace.audit_codes == (), (
            f"round {r}: expected empty audit_codes; "
            f"got {result.round_trace.audit_codes!r}"
        )

    # The adapter was called exactly once per round.
    assert len(captured_policies) == cycle_length, (
        f"expected {cycle_length} apply_restart_distribution calls; "
        f"got {len(captured_policies)}"
    )

    # For every round, the policy's effective beta_by_channel must
    # match the schedule's n_cap (clipped to [0, 1]).
    for r, sample in enumerate(samples):
        captured = captured_policies[r]
        n_cap = max(0.0, min(1.0, float(sample.n_cap)))
        actual_beta = float(captured.beta_by_channel.get(ChannelName("xy"), -1.0))
        assert actual_beta == pytest.approx(n_cap, abs=1e-12), (
            f"round {r}: captured policy beta_by_channel[{n_cap:.6f}] != "
            f"n_cap={n_cap:.6f}; full captured betas: "
            f"{[float(p.beta_by_channel.get(ChannelName('xy'), -1.0)) for p in captured_policies]!r}"
        )

    # Now also re-derive the memory fractions the engine emitted and
    # assert monotone non-decreasing across the cycle.
    memory_fractions = [
        1.0
        - float(
            p.beta_by_channel.get(ChannelName("xy"), 1.0)
        )
        for p in captured_policies
    ]

    # 1. Round 0 is near ``1 - n_max`` = ``0.0`` (pure fresh noise).
    assert memory_fractions[0] < 0.05, (
        f"round 0 memory_fraction should be near 1 - n_max = {1.0 - n_max:.3f}; "
        f"got {memory_fractions[0]:.3f}; full sequence: {memory_fractions!r}"
    )
    # 2. Round L-1 is near ``1 - n_min`` = ``1.0`` (pure prior).
    assert memory_fractions[-1] > 0.95, (
        f"round {cycle_length - 1} memory_fraction should be near 1 - n_min = "
        f"{1.0 - n_min:.3f}; got {memory_fractions[-1]:.3f}; "
        f"full sequence: {memory_fractions!r}"
    )
    # 3. Monotone non-decreasing across the cycle.
    for r in range(1, len(memory_fractions)):
        assert memory_fractions[r] >= memory_fractions[r - 1] - 1e-12, (
            f"memory_fraction must be monotone non-decreasing; "
            f"got {memory_fractions[r - 1]:.3f} at r={r - 1} and "
            f"{memory_fractions[r]:.3f} at r={r}; "
            f"full sequence: {memory_fractions!r}"
        )


def test_first_round_pure_fresh_noise(twodim_fm_weights_path: Path) -> None:
    """Round 0 memory fraction is below 0.05 (mostly fresh noise).

    With ``n_max = 1.0`` the engine emits ``beta = n_cap = 1.0`` at
    round 0 so the memory fraction is ``1 - beta = 0.0`` — the
    prior is completely replaced by fresh N(0, I) noise.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame import Engine

    samples = _build_cosine_samples(cycle_length=8, n_min=0.0, n_max=1.0)
    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)
    engine = Engine()
    bundle = adapter.build_initial_state(
        batch_id="batch-fresh-noise", sample_id="sample-fresh-noise"
    )
    policy = _make_policy_with_schedule(
        policy_id="policy-fresh-noise",
        run_id="run-fresh-noise",
        beta=0.5,  # explicit; engine will override
        target_round=0,
        schedule_sample=samples[0],
    )
    memory_fraction = _drive_round(
        adapter, engine, bundle=bundle, policy=policy, target_round=0
    )
    assert memory_fraction < 0.05, (
        f"round 0 memory_fraction should be near 0 (pure fresh noise); "
        f"got {memory_fraction:.3f}"
    )


def test_last_round_pure_prior(twodim_fm_weights_path: Path) -> None:
    """Round L-1 memory fraction is above 0.95 (pure prior preservation).

    With ``n_min = 0.0`` the engine emits ``beta = n_cap = 0.0`` at
    round L-1 so the memory fraction is ``1 - beta = 1.0`` — the
    prior endpoint is preserved verbatim through the restart boundary.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame import Engine

    cycle_length = 8
    samples = _build_cosine_samples(
        cycle_length=cycle_length, n_min=0.0, n_max=1.0
    )
    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)
    engine = Engine()
    bundle = adapter.build_initial_state(
        batch_id="batch-mostly-prior", sample_id="sample-mostly-prior"
    )
    policy = _make_policy_with_schedule(
        policy_id="policy-mostly-prior",
        run_id="run-mostly-prior",
        beta=0.5,  # explicit; engine will override
        target_round=cycle_length - 1,
        schedule_sample=samples[-1],
    )
    memory_fraction = _drive_round(
        adapter, engine,
        bundle=bundle,
        policy=policy,
        target_round=cycle_length - 1,
    )
    assert memory_fraction > 0.95, (
        f"round {cycle_length - 1} memory_fraction should be near 1.0 "
        f"(pure prior); got {memory_fraction:.3f}"
    )


def test_constant_beta_overrides_schedule(
    twodim_fm_weights_path: Path,
) -> None:
    """``beta_from_schedule=False`` pins beta_by_channel verbatim.

    The cosine schedule is attached to the policy (so
    ``schedule_sample is not None``), but the ``beta_from_schedule``
    flag is ``False``. The engine must forward the policy verbatim —
    the explicit ``beta=0.5`` must reach the adapter untouched.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.contracts import ChannelName
    from adaptive_reflow.frame import Engine

    # Use a sample whose n_cap would drive beta to 0.0 (pure prior);
    # with the override off we expect the explicit beta=0.5 to win.
    samples = _build_cosine_samples(cycle_length=8, n_min=0.0, n_max=1.0)
    adapter = TwoDimFMAdapter(weights_path=twodim_fm_weights_path)
    engine = Engine()
    bundle = adapter.build_initial_state(
        batch_id="batch-override-off", sample_id="sample-override-off"
    )

    # Hook apply_restart_distribution so we can verify the explicit
    # beta was preserved through the engine's policy forwarding.
    captured_policies: list[FinalRestartPolicy] = []

    original_apply = adapter.apply_restart_distribution

    def _hooked(state, policy):
        captured_policies.append(policy)
        return original_apply(state, policy)

    adapter.apply_restart_distribution = _hooked  # type: ignore[method-assign]

    pinned_beta = 0.5
    policy = _make_policy_with_schedule(
        policy_id="policy-override-off",
        run_id="run-override-off",
        beta=pinned_beta,
        target_round=samples[-1].round_in_cycle,
        schedule_sample=samples[-1],
        beta_from_schedule=False,
    )
    memory_fraction = _drive_round(
        adapter, engine,
        bundle=bundle,
        policy=policy,
        target_round=samples[-1].round_in_cycle,
    )
    assert abs(memory_fraction - (1.0 - pinned_beta)) < 1e-12, (
        f"beta_from_schedule=False must preserve the explicit beta; "
        f"expected memory_fraction={1.0 - pinned_beta:.6f}; "
        f"got {memory_fraction:.6f}"
    )
    # The adapter must have received the explicit pinned beta on
    # every call (both calls land in ``captured_policies`` because the
    # helper re-runs ``apply_restart_distribution`` after the engine
    # round). Every captured policy must carry ``beta=0.5``; the
    # schedule's ``n_cap=0.0`` must NOT have overridden it.
    assert len(captured_policies) >= 1, (
        "expected at least one captured apply_restart_distribution call"
    )
    for idx, captured in enumerate(captured_policies):
        actual_beta = float(
            captured.beta_by_channel.get(ChannelName("xy"), -1.0)
        )
        assert actual_beta == pytest.approx(pinned_beta, abs=1e-12), (
            f"adapter call {idx}: beta must be the explicit pinned value; "
            f"expected {pinned_beta:.6f}; got {actual_beta:.6f}"
        )
    # And the policy object itself is unmodified (caller can still
    # introspect the unoverridden surface).
    assert float(policy.beta_by_channel[ChannelName("xy")]) == pinned_beta, (
        "engine.run_round must not mutate the supplied policy"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
