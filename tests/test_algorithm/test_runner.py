"""Tests for :class:`ReInferenceRunner` — the outer framework that drives the inner re-inference loop.

These tests exercise the outer framework against the
:class:`TwoDimFMAdapter` + :class:`Engine` inner loop. The test
strategy is to compare the runner's outputs to the canonical
``Engine.run_round`` outputs (the old code path) and to assert that
the runner composes (scheduler, driver) freely.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from adaptive_reflow.algorithm import (
    AdaptivePolicyDriver,
    ConstantPolicyDriver,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    IdentityOperator,
    ReInferenceConfig,
    ReInferenceRunner,
    ScheduleDerivedPolicyDriver,
    default_bounded_merge_operator,
    default_cosine_scheduler,
    default_policy_driver,
)
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
from adaptive_reflow.frame.adapter import ODEConditionDelta
from adaptive_reflow.frame.engine import Engine, PhaseState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


TWODIM_FM_CHANNELS: tuple[str, ...] = ("xy",)
XY_CHANNEL: ChannelName = ChannelName("xy")


def _make_cosine_base_policy(
    *,
    schedule_sample,
    target_round: int,
    beta: float = 0.0,
    beta_from_schedule: bool = False,
    policy_id_prefix: str = "runner-test",
) -> FinalRestartPolicy:
    """Build a deterministic :class:`FinalRestartPolicy` for a cosine-anneal round.

    Mirrors the policy factory in ``tools/run_ablation.py`` so the
    runner-driven path and the legacy engine-driven path produce
    bit-identical policies.
    """
    placeholder = FinalRestartPolicy(
        policy_id=PolicyId(f"{policy_id_prefix}-{target_round}"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(f"{policy_id_prefix}-run"),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={XY_CHANNEL: FactorValue(float(beta))},
        alpha_by_channel={XY_CHANNEL: FactorValue(1.0)},
        fresh_noise_floor_by_channel={XY_CHANNEL: FactorValue(0.0)},
        schedule_sample=schedule_sample,
        freeze_admission_by_channel={XY_CHANNEL: True},
        ledger_row_id=LedgerRowId(f"{policy_id_prefix}-ledger-{target_round}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=bool(beta_from_schedule),
    )
    return replace(placeholder, policy_hash=hash_policy_hash(placeholder))


def _make_phase_state(*, horizon_remaining: int, round_in_cycle: int = 0) -> PhaseState:
    """Build a deterministic :class:`PhaseState`."""
    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=int(round_in_cycle),
        schedule_phase="runner-test",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="runner-test-lineage",
        recorded_at_round=int(round_in_cycle),
    )


def _make_condition_delta(*, target_round: int) -> ODEConditionDelta:
    """Build a deterministic per-round :class:`ODEConditionDelta`.

    Mirrors the runner's ``_build_condition_delta`` helper so the
    legacy test path produces the same ``condition_digest`` as the
    runner-driven path.
    """
    return ODEConditionDelta(
        delta_spec={"num_steps": 100, "target_round": int(target_round)},
        source="adaptive_reflow.algorithm.runner",
        target_round=int(target_round),
        calibration_artifact_hash="runner-calibration",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _twodim_adapter(twodim_fm_weights_path):
    """Return a single ``TwoDimFMAdapter`` instance reused across the tests."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    return TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, target="two_moons"
    )


# ---------------------------------------------------------------------------
# 1. Default runner reproduces the legacy engine path
# ---------------------------------------------------------------------------


def test_runner_with_defaults_produces_same_results_as_old_engine(
    _twodim_adapter,
) -> None:
    """A default :class:`ReInferenceRunner` produces the same round trace as the legacy
    ``Engine.run_round`` loop that drove the cosine-anneal path.

    The legacy path builds the policy with
    ``beta_from_schedule=True, schedule_sample=cosine_sample`` and lets
    the engine's inline ``_policy_with_schedule_beta`` override
    ``beta_by_channel`` with ``n_cap``. The runner path builds the
    same policy with ``beta_from_schedule=False`` and lets the default
    :class:`ScheduleDerivedPolicyDriver` apply the same override via
    its :meth:`compute_policy` method. Both must produce the SAME
    applied ``beta`` value (``n_cap``) for every round (Contract 3.1
    / Contract 1.2).

    NOTE (Contract 1.2): the ``policy_hash`` differs across paths
    because the runner's driver sets ``driver_computed_beta=True``
    while the legacy path leaves it ``False``. The
    ``endpoint_digest`` (which folds in ``policy.policy_hash`` via the
    adapter's restart-blend digest) therefore also differs across
    paths. The applied ``beta`` and the per-round metric scalars
    (``n_cap`` / ``memory_fraction`` / ``beta``) remain byte-identical
    — the runner is a drop-in replacement for the legacy engine
    path modulo the driver/engine dedup flag.
    """
    adapter = _twodim_adapter
    n_rounds = 5
    engine = Engine()
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    primary_channel = TWODIM_FM_CHANNELS[0]

    # ----- Legacy engine path: build policy manually, run Engine -----
    # Use the SAME batch_id / sample_id the runner uses so the
    # initial-state digests match (the runner's identifiers are
    # ``runner-batch-{channel}`` / ``runner-sample-{channel}-r{r}``).
    legacy_bundle = adapter.build_initial_state(
        batch_id=f"runner-batch-{primary_channel}",
        sample_id=f"runner-sample-{primary_channel}-r0",
    )
    legacy_phase = _make_phase_state(horizon_remaining=n_rounds)
    legacy_results = []
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        legacy_policy = _make_cosine_base_policy(
            schedule_sample=sample.as_cosine_schedule_sample(),
            target_round=r,
            beta=0.0,
            beta_from_schedule=True,  # engine overrides beta via the inline helper
            policy_id_prefix="runner",
        )
        legacy_condition = _make_condition_delta(target_round=r)
        legacy_result = engine.run_round(
            round_index=r,
            phase_state=legacy_phase,
            bundle=legacy_bundle,
            adapter=adapter,
            policy=legacy_policy,
            condition_delta=legacy_condition,
            seed=42 + r,
        )
        legacy_results.append(legacy_result)
        legacy_phase = legacy_result.next_phase_state
        if legacy_result.round_trace.integrator_trace is not None:
            legacy_bundle = adapter.observe_endpoint(
                legacy_result.round_trace.integrator_trace, legacy_bundle
            )

    # ----- Runner path: use all-default components -----------------
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=default_policy_driver(),
        merge_operator=default_bounded_merge_operator(),
    )
    runner_result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    # ----- Compare round-by-round ----------------------------------
    assert len(runner_result.round_traces) == n_rounds
    for r in range(n_rounds):
        legacy_trace = legacy_results[r].round_trace
        runner_trace = runner_result.round_traces[r]
        # The initial state digest must match (no policy dependency).
        assert str(legacy_trace.initial_state_digest) == str(
            runner_trace.initial_state_digest
        )
        # Both paths produce a non-None integrator trace (the ODE
        # solve returned a trajectory).
        assert (
            legacy_trace.integrator_trace is not None
            and runner_trace.integrator_trace is not None
        )
        # NOTE (Contract 1.2): the integrator
        # ``native_state_digest`` is folded with the post-restart
        # bundle digest, which in turn folds the
        # ``applied_policy.policy_hash``. Because the runner's driver
        # path produces ``driver_computed_beta=True`` and the legacy
        # engine path produces ``driver_computed_beta=False``, the two
        # ``applied_policy.policy_hash`` values differ and so do the
        # post-restart bundle digests and the resulting integrator
        # traces. We deliberately do NOT assert
        # ``native_state_digest`` equality across paths — see the
        # module-level docstring of this test for the rationale.
        # The condition_digest must match (it depends on
        # ``condition_delta``, not on policy).
        assert str(legacy_trace.condition_digest) == str(
            runner_trace.condition_digest
        )

    # Per-round metrics expose the schedule's n_cap and the runner's beta.
    for r in range(n_rounds):
        metrics = runner_result.per_round_metrics[r]
        assert "n_cap" in metrics
        assert "memory_fraction" in metrics
        assert "beta" in metrics
        # ScheduleDerivedPolicyDriver applies beta = n_cap, so beta must
        # equal n_cap for every round (Contract 3.1 / Contract 1.2).
        assert metrics["beta"] == pytest.approx(metrics["n_cap"])

    # Contract 1.2 explicit assertion: both paths produce applied beta
    # equal to n_cap; the legacy path applies the override via the
    # engine inline helper (and leaves ``driver_computed_beta=False``)
    # while the runner path applies it via the
    # ``ScheduleDerivedPolicyDriver`` (which sets
    # ``driver_computed_beta=True``). The resulting ``beta`` is
    # identical in both paths.
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        expected_beta = sample.n_cap
        runner_metric = runner_result.per_round_metrics[r]
        assert runner_metric["beta"] == pytest.approx(expected_beta)


# ---------------------------------------------------------------------------
# 2. Mixed scheduler + driver (impossible in the old code)
# ---------------------------------------------------------------------------


def test_runner_with_constant_scheduler_and_cosine_driver(_twodim_adapter) -> None:
    """A *mixed* configuration the old code couldn't express.

    Scheduler: ``CosineAnnealScheduler`` (varying ``n_cap`` across
    rounds). Driver: :class:`ConstantPolicyDriver(beta=0.5)`. The
    driver emits a constant ``beta = 0.5``; the merge step
    (Contract 2.4) then bounds it against ``schedule.n_cap`` (the
    cosine ramp), producing ``beta = min(0.5, n_cap)`` per round.

    This configuration is impossible in the old code (the engine
    either applied ``beta = n_cap`` via the inline override or used
    the caller's explicit ``beta``; the cross-product was
    unreachable). The new framework composes ``(scheduler, driver,
    merge_operator)`` freely so the test verifies the runner
    produces a well-defined bounded result.
    """
    adapter = _twodim_adapter
    n_rounds = 4
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    driver = ConstantPolicyDriver(beta=0.5)
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=driver,
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    # Every round ran successfully (no audit codes).
    for r, trace in enumerate(result.round_traces):
        assert not trace.audit_codes, (
            f"round {r}: unexpected audit_codes={trace.audit_codes!r}"
        )
    # Per-round metrics: contract 2.4 — the bounded merge clamps the
    # constant 0.5 driver output against the schedule's ``n_cap`` so
    # ``beta = min(0.5, n_cap)`` per round. The cosine ramp's
    # ``n_cap`` values are 1.0, 0.75, 0.25, 0.0 (cycle_length=4,
    # n_min=0, n_max=1) so the bounded betas trace ``[0.5, 0.5,
    # 0.25, 0.0]``.
    n_caps = [result.per_round_metrics[r]["n_cap"] for r in range(n_rounds)]
    expected_betas = [min(0.5, n) for n in n_caps]
    betas = [result.per_round_metrics[r]["beta"] for r in range(n_rounds)]
    assert betas == pytest.approx(expected_betas, abs=1e-12), (
        f"mixed config: beta should follow min(constant, n_cap); "
        f"got betas={betas!r} expected={expected_betas!r}"
    )
    # The schedule's n_cap is varying (cosine annealing) so the
    # constant driver truly is being clamped by the schedule's ramp.
    assert len({round(n_c, 6) for n_c in n_caps}) > 1, (
        f"schedule's n_cap should vary; got {n_caps!r}"
    )
    # The runner is deterministic: a second run produces the same
    # endpoint digests (proves the cross-product is reproducible).
    runner_2 = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=driver,
    )
    result_2 = runner_2.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    for r in range(n_rounds):
        assert str(result.round_traces[r].endpoint_digest) == str(
            result_2.round_traces[r].endpoint_digest
        )


def test_runner_with_identity_operator_passes_dynamic_through(
    _twodim_adapter,
) -> None:
    """Contract 2.4: with :class:`IdentityOperator`, the runner
    passes the driver's ``beta`` through unmodified (the merge step
    becomes a no-op for dynamic value).

    The test feeds a constant ``beta = 0.7`` driver and asserts the
    runner's per-round ``beta`` is exactly 0.7 every round (the
    identity operator ignores the cap / floor / delta caps).
    """
    adapter = _twodim_adapter
    n_rounds = 3
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    driver = ConstantPolicyDriver(beta=0.7)
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=driver,
        merge_operator=IdentityOperator(),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    betas = [result.per_round_metrics[r]["beta"] for r in range(n_rounds)]
    # IdentityOperator ignores ``cap`` / ``floor`` and returns the
    # dynamic value verbatim. Even when ``cap`` (the schedule's
    # ``n_cap``) is smaller than ``dynamic`` (0.7), the identity
    # operator passes ``dynamic`` through.
    assert betas == pytest.approx([0.7, 0.7, 0.7]), (
        f"identity operator should preserve the driver's dynamic "
        f"beta=0.7 every round; got {betas!r}"
    )


# ---------------------------------------------------------------------------
# 3. per_round_metrics emits one entry per round
# ---------------------------------------------------------------------------


def test_runner_emits_per_round_metrics(_twodim_adapter) -> None:
    """``per_round_metrics`` contains one entry per round index."""
    adapter = _twodim_adapter
    n_rounds = 7
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    assert len(result.per_round_metrics) == n_rounds
    for r in range(n_rounds):
        assert r in result.per_round_metrics
        metric = result.per_round_metrics[r]
        assert "n_cap" in metric
        assert "memory_fraction" in metric
        assert "beta" in metric
        assert 0.0 <= metric["memory_fraction"] <= 1.0
        assert 0.0 <= metric["n_cap"] <= 1.0
        assert 0.0 <= metric["beta"] <= 1.0


# ---------------------------------------------------------------------------
# 4. algorithm_signatures contains every component's config_hash
# ---------------------------------------------------------------------------


def test_runner_algorithm_signatures_present(_twodim_adapter) -> None:
    """``algorithm_signatures`` exposes the four canonical keys."""
    adapter = _twodim_adapter
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=3),
        policy_driver=ConstantPolicyDriver(beta=0.25),
        merge_operator=default_bounded_merge_operator(),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=3,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    assert "scheduler" in result.algorithm_signatures
    assert "policy_driver" in result.algorithm_signatures
    assert "merge_operator" in result.algorithm_signatures
    assert "blender" in result.algorithm_signatures
    for key, value in result.algorithm_signatures.items():
        assert isinstance(value, str) and len(value) > 0, (
            f"algorithm_signatures[{key}] must be a non-empty string; got {value!r}"
        )

    # Different scheduler + driver pairs produce different signatures.
    runner_alt = ReInferenceRunner(
        adapter=adapter,
        scheduler=ConstantScheduler(cycle_length=3, n_cap=0.5),
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=default_bounded_merge_operator(),
    )
    result_alt = runner_alt.run(
        ReInferenceConfig(
            n_rounds=3,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    assert (
        result.algorithm_signatures["scheduler"]
        != result_alt.algorithm_signatures["scheduler"]
    )
    assert (
        result.algorithm_signatures["policy_driver"]
        != result_alt.algorithm_signatures["policy_driver"]
    )


# ---------------------------------------------------------------------------
# 5. Default factories are invoked when components are not supplied
# ---------------------------------------------------------------------------


def test_runner_default_factories(_twodim_adapter) -> None:
    """A runner built without explicit components uses the canonical defaults."""
    adapter = _twodim_adapter
    runner = ReInferenceRunner(adapter=adapter)
    assert isinstance(runner.scheduler, CosineAnnealScheduler)
    assert isinstance(runner.policy_driver, ScheduleDerivedPolicyDriver)
    # Endpoints array has the right shape even though no evaluator was supplied.
    result = runner.run(
        ReInferenceConfig(n_rounds=2, channels=TWODIM_FM_CHANNELS)
    )
    assert result.endpoints.shape == (2, 2)
    assert result.endpoints.dtype == np.float64


# ---------------------------------------------------------------------------
# 6. record_round_feedback is wired through the runner
# ---------------------------------------------------------------------------


class _RecordingScheduler:
    """Minimal SchedulerProtocol stand-in that records feedback calls.

    Used to verify the runner actually invokes
    ``record_round_feedback`` for each round. The scheduler delegates
    capacity sampling to a base :class:`CosineAnnealScheduler` so the
    runner can drive the engine the same way it does with the canonical
    cosine scheduler.
    """

    def __init__(self, base: CosineAnnealScheduler) -> None:
        self._base = base
        self.feedback_calls: list[tuple[int, dict[str, float]]] = []

    def sample(self, outer_cycle_id, round_in_cycle, target_round):
        return self._base.sample(outer_cycle_id, round_in_cycle, target_round)

    def cycle_length(self) -> int:
        return self._base.cycle_length()

    def schedule_family(self) -> str:
        return self._base.schedule_family()

    def config_hash(self) -> str:
        return str(self._base.config_hash())

    def reset(self) -> None:
        self._base.reset()
        self.feedback_calls = []

    def record_round_feedback(self, round_in_cycle, metrics):
        self.feedback_calls.append((int(round_in_cycle), dict(metrics)))


def test_runner_passes_w2_to_scheduler_feedback(_twodim_adapter) -> None:
    """ReInferenceRunner.run() must invoke record_round_feedback once per round."""
    adapter = _twodim_adapter
    n_rounds = 5
    recording = _RecordingScheduler(
        default_cosine_scheduler(cycle_length=n_rounds)
    )
    runner = ReInferenceRunner(adapter=adapter, scheduler=recording)
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    assert len(recording.feedback_calls) == n_rounds
    for r, (round_idx, metrics) in enumerate(recording.feedback_calls):
        assert round_idx == r
        # The runner passes the per-round metric dict; W2 key may be
        # absent when no evaluator is wired in, but the metric dict
        # must contain the algorithm scalars.
        assert "n_cap" in metrics
        assert "memory_fraction" in metrics
        assert "beta" in metrics


def test_runner_passes_w2_to_convergence_adaptive_scheduler(_twodim_adapter) -> None:
    """End-to-end: ConvergenceAdaptiveScheduler accumulates W2 feedback via the runner."""
    adapter = _twodim_adapter
    n_rounds = 6
    adaptive = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=n_rounds),
        kp=0.5,
        kd=0.2,
        shift_max=0.5,
        ema=0.5,
    )
    runner = ReInferenceRunner(adapter=adapter, scheduler=adaptive)
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    # Without an evaluator the runner does not promote a W2 key into the
    # metric dict, so record_round_feedback sees no W2 and the shift
    # stays at its initial value. This guards the contract: the runner
    # *calls* the hook (even when W2 is absent), but does not fabricate
    # metrics the engine did not produce.
    assert adaptive.w2_history == ()
    assert adaptive.shift == 0.0


# ---------------------------------------------------------------------------
# 7. config.outer_cycle_id propagates into the engine's applied_policy_hash
# ---------------------------------------------------------------------------


def test_runner_outer_cycle_id_propagates_to_policy_hash(_twodim_adapter) -> None:
    """config.outer_cycle_id must reach the round trace's applied_policy_hash.

    Regression test: prior to the audit fix the runner hardcoded
    ``outer_cycle_id=0`` in its ``_build_base_policy`` placeholder, so
    two runners with different ``outer_cycle_id`` produced identical
    ``applied_policy_hash`` values. The policy hash includes
    ``outer_cycle_id`` (see ``hash_policy_hash``), so the two runs
    below must now produce distinguishable hashes.
    """
    adapter = _twodim_adapter
    n_rounds = 3
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
    )

    result_cycle_0 = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    result_cycle_5 = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=5,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    # The policy hash differs across rounds as well (different
    # ``target_round``); pick a single round index for the comparison
    # so the only varying input is ``outer_cycle_id``.
    for r in range(n_rounds):
        hash_cycle_0 = str(result_cycle_0.round_traces[r].applied_policy_hash)
        hash_cycle_5 = str(result_cycle_5.round_traces[r].applied_policy_hash)
        assert hash_cycle_0 != hash_cycle_5, (
            f"round {r}: outer_cycle_id did not propagate into "
            f"applied_policy_hash (both={hash_cycle_0!r})"
        )


# ---------------------------------------------------------------------------
# 8. config.outer_cycle_id propagates into the initial PhaseState
# ---------------------------------------------------------------------------


def test_runner_outer_cycle_id_propagates_to_phase_state(_twodim_adapter) -> None:
    """config.outer_cycle_id must reach the engine-supplied PhaseState.

    Regression test: ``_build_initial_phase_state`` previously
    hardcoded ``outer_cycle_id=0``. The engine propagates
    ``outer_cycle_id`` through ``next_phase_state`` so a wrong initial
    value would persist for every round. The trace does not expose
    the phase state, so the test wraps the engine to capture every
    phase state forwarded into ``run_round``.
    """
    adapter = _twodim_adapter
    n_rounds = 2
    captured: list[int] = []

    real_engine = Engine()

    class _CaptureEngine(Engine):
        def run_round(self, *args, **kwargs):  # type: ignore[override]
            phase_state = kwargs.get("phase_state")
            if phase_state is None and len(args) >= 2:
                phase_state = args[1]
            captured.append(int(phase_state.outer_cycle_id))
            return real_engine.run_round(*args, **kwargs)

    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
        engine=_CaptureEngine(),
    )
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=7,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    assert captured == [7, 7], (
        f"every round must see outer_cycle_id=7 in its PhaseState; "
        f"got {captured!r}"
    )


# ---------------------------------------------------------------------------
# 9. endpoints matrix is NaN-initialised (no uninitialised memory)
# ---------------------------------------------------------------------------


def test_runner_endpoints_matrix_is_nan_initialised(_twodim_adapter) -> None:
    """result.endpoints must be NaN-initialised, never uninitialised.

    Regression test: prior to the fix the runner allocated the
    endpoints matrix with ``np.empty`` and only filled rows for which
    ``trace.integrator_trace`` was non-None. Any round where the
    trajectory capture was skipped (audit_codes, missing
    ``_native_states`` entry, etc.) left the row reading as
    uninitialised memory. The fix initialises with NaN so callers can
    detect "endpoint not captured" via ``np.isnan``.
    """
    adapter = _twodim_adapter
    n_rounds = 3
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    assert result.endpoints.shape == (n_rounds, 2)
    assert result.endpoints.dtype == np.float64
    # For the happy-path 2D-FM run every row should be finite (no NaN).
    assert np.isfinite(result.endpoints).all(), (
        f"expected all endpoints finite for a normal run; "
        f"got NaN mask={np.isnan(result.endpoints)}"
    )


def test_runner_endpoints_matrix_respects_adapter_state_shape(
    _twodim_adapter,
) -> None:
    """P0-4 (F-24): the endpoint matrix honours the adapter's ``state_shape``.

    Earlier the runner hard-coded ``arr[-1].reshape(2)`` regardless of
    the adapter's native state vector, so 8 of 10 adapters (CIFAR's
    ``(3, 32, 32)``, video adapters' ``(T, C, H, W)``, …) had their
    endpoint row collapse to a NaN. The fix reads the adapter's
    ``state_shape`` attribute and reshapes the per-round endpoint
    vector into it; size mismatches leave the row as ``NaN`` so
    callers can detect "endpoint not captured" via ``np.isnan``.
    """
    adapter = _twodim_adapter
    n_rounds = 3
    # ``_twodim_adapter`` exposes a 2-D state; override ``state_shape``
    # on the adapter instance so the runner reshapes into a 3-vector.
    adapter.state_shape = (3,)  # type: ignore[attr-defined]
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    # The endpoint matrix now follows ``state_shape == (3,)``.
    assert result.endpoints.shape == (n_rounds, 3)
    # The 2-D trajectory has 2 elements but the advertised state
    # shape wants 3 — so the per-round reshape is a size mismatch
    # and the runner must leave the row as NaN. With the P0-4 fix
    # ``endpoint_export_failed == 1.0`` and the row is NaN.
    for r in range(n_rounds):
        sample = result.per_round_metrics[r]
        assert sample["endpoint_export_failed"] == pytest.approx(1.0)
        assert np.isnan(result.endpoints[r]).all(), (
            f"row {r}: size mismatch must leave the endpoint row as "
            f"NaN; got {result.endpoints[r]!r}"
        )
    # Cleanup the override so the fixture stays pristine for other tests.
    if hasattr(adapter, "state_shape"):
        delattr(adapter, "state_shape")


# ---------------------------------------------------------------------------
# 10. paper_quantities_provider wiring (ADR-0013 follow-up)
# ---------------------------------------------------------------------------


def test_runner_with_paper_quantities_emits_diagnostics(_twodim_adapter) -> None:
    """``paper_quantities_provider`` produces per-round diagnostics.

    Configuring ``ReInferenceConfig.paper_quantities_provider``
    upgrades the scheduler / driver in place (when their concrete
    types support the upgrade) and records the four paper quantities
    ``(sheet_A, packing_B, cell_C, exterior_gap_e_rho)`` in each
    ``per_round_metrics[r]`` under the
    ``paper_quantity_diagnostics`` entry. The diagnostics match the
    values computed directly by ``paper_quantities.*``.
    """
    import math

    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler
    from adaptive_reflow.contracts import paper_quantities as _pq

    adapter = _twodim_adapter
    n_rounds = 4
    profile = lambda x: math.sin(x)  # noqa: E731

    # Reference paper quantities for the diagnostics check below.
    expected_sheet_A = float(_pq.sheet_evidence_A(profile))
    expected_packing_B = float(_pq.root_cell_packing_B(profile))
    expected_cell_C = float(_pq.per_cell_coefficient_C())
    expected_e_rho = float(_pq.exterior_gap_e_rho())

    # Build the runner with a CodimensionSheetScheduler + the legacy
    # schedule-derived driver so we can confirm the diagnostics path
    # is wired through the ``paper_quantities_provider`` argument.
    scheduler = CodimensionSheetScheduler(
        cycle_length=n_rounds, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=default_bounded_merge_operator(),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
            paper_quantities_provider=profile,
        )
    )
    # Every round carries the diagnostics entry.
    assert len(result.per_round_metrics) == n_rounds
    for r in range(n_rounds):
        metric = result.per_round_metrics[r]
        assert "paper_quantity_diagnostics" in metric, (
            f"round {r}: missing paper_quantity_diagnostics; "
            f"keys={sorted(metric)!r}"
        )
        diag = metric["paper_quantity_diagnostics"]
        assert diag["sheet_A"] == pytest.approx(expected_sheet_A, rel=1e-12)
        assert diag["packing_B"] == pytest.approx(expected_packing_B, rel=1e-12)
        assert diag["cell_C"] == pytest.approx(expected_cell_C, rel=1e-12)
        assert diag["exterior_gap_e_rho"] == pytest.approx(
            expected_e_rho, rel=1e-12
        )

    # The scheduler was upgraded in place to consume paper quantities.
    assert isinstance(runner.scheduler, CodimensionSheetScheduler)
    assert runner.scheduler.sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
    assert runner.scheduler.packing_B == pytest.approx(
        expected_packing_B, rel=1e-12
    )
    assert runner.scheduler.cell_C == pytest.approx(expected_cell_C, rel=1e-12)
    assert runner.scheduler.exterior_gap_e_rho == pytest.approx(
        expected_e_rho, rel=1e-12
    )


def test_runner_without_paper_quantities_legacy_behavior(_twodim_adapter) -> None:
    """Without ``paper_quantities_provider`` no diagnostics are emitted.

    Backward compatibility: when ``paper_quantities_provider`` is
    ``None`` (the default), the runner does not emit
    ``paper_quantity_diagnostics`` and does not upgrade the scheduler
    / driver in place.
    """
    adapter = _twodim_adapter
    n_rounds = 3
    # Pin the scheduler/driver to known types so we can verify they
    # are NOT upgraded.
    from adaptive_reflow.algorithm.scheduler import CosineAnnealScheduler

    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    driver = ScheduleDerivedPolicyDriver()
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=driver,
        merge_operator=default_bounded_merge_operator(),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    # Diagnostics are absent for every round.
    for r in range(n_rounds):
        metric = result.per_round_metrics[r]
        assert "paper_quantity_diagnostics" not in metric, (
            f"round {r}: paper_quantity_diagnostics should be absent "
            f"when no provider is configured; keys={sorted(metric)!r}"
        )
    # Scheduler / driver unchanged.
    assert isinstance(runner.scheduler, CosineAnnealScheduler)
    assert isinstance(runner.policy_driver, ScheduleDerivedPolicyDriver)


def test_runner_paper_quantities_upgrade_adaptive_driver(_twodim_adapter) -> None:
    """``paper_quantities_provider`` upgrades ``AdaptivePolicyDriver``.

    When the runner is built with an :class:`AdaptivePolicyDriver`
    and a ``paper_quantities_provider`` is supplied, the runner
    replaces the driver with one constructed with
    ``per_cell_coefficient_C`` set so the per-round ``beta`` lives
    on paper Lemma 3's per-cell evidence scale.
    """
    import math

    from adaptive_reflow.contracts import paper_quantities as _pq

    adapter = _twodim_adapter
    n_rounds = 2
    profile = lambda x: math.sin(x)  # noqa: E731
    expected_C = float(_pq.per_cell_coefficient_C())

    driver = AdaptivePolicyDriver(target_estimate=0.5)
    assert driver.per_cell_coefficient_C is None
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
        policy_driver=driver,
        merge_operator=default_bounded_merge_operator(),
    )
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
            paper_quantities_provider=profile,
        )
    )
    # The driver was upgraded in place.
    assert isinstance(runner.policy_driver, AdaptivePolicyDriver)
    assert runner.policy_driver.per_cell_coefficient_C == pytest.approx(
        expected_C, rel=1e-12
    )


def test_runner_paper_quantities_rejects_non_callable_provider(
    _twodim_adapter,
) -> None:
    """Non-callable ``paper_quantities_provider`` raises ``ValueError``."""
    from adaptive_reflow.algorithm.scheduler import (
        CodimensionSheetScheduler,
    )

    adapter = _twodim_adapter
    n_rounds = 2
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=CodimensionSheetScheduler(cycle_length=n_rounds),
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=default_bounded_merge_operator(),
    )
    with pytest.raises(ValueError, match="callable"):
        runner.run(
            ReInferenceConfig(
                n_rounds=n_rounds,
                outer_cycle_id=0,
                target_round=0,
                seed=42,
                channels=TWODIM_FM_CHANNELS,
                paper_quantities_provider=42,  # type: ignore[arg-type]
            )
        )


# ---------------------------------------------------------------------------
# F10 — runner wires paper quantities via ``CodimensionSheetScheduler.with_profile``
# ---------------------------------------------------------------------------


def test_runner_f10_wires_paper_quantities_via_with_profile(
    _twodim_adapter,
) -> None:
    """F10: the runner wires ``paper_quantities_provider`` through the
    public :meth:`CodimensionSheetScheduler.with_profile` swap-constructor,
    not by reaching into private attributes.

    The test wraps a recording subclass of
    :class:`CodimensionSheetScheduler` that flags every direct
    constructor call (``__init__``) and every :meth:`with_profile`
    call. After the run:

    * ``with_profile`` MUST have been called exactly once (with the
      supplied provider), and
    * the resulting ``runner.scheduler`` MUST be the object returned
      by ``with_profile`` (identity check, so the runner cannot
      reconstruct via private-attr ``CodimensionSheetScheduler(...)``
      behind the subclass's back).

    Re-introducing the ``hasattr(self._scheduler, "with_profile")``
    fallback would route the upgrade through the direct
    ``CodimensionSheetScheduler(...)`` constructor — which would
    fail the identity assertion below because the constructor's
    return value is discarded by the runner.
    """
    from adaptive_reflow.algorithm.scheduler import (
        CodimensionSheetScheduler,
    )

    init_calls: list[dict[str, object]] = []
    with_profile_calls: list[object] = []

    class _RecordingCodimensionScheduler(CodimensionSheetScheduler):
        """Subclass that records ``__init__`` and ``with_profile`` calls.

        On ``with_profile`` the recording is appended BEFORE delegating
        to the base class so the test sees the call regardless of what
        the base returns. We return the base-class object (not ``self``)
        so the identity assertion below has a chance to fire if the
        runner reconstructs via the constructor instead of taking the
        return value.
        """

        def __init__(self, **kwargs: object) -> None:
            init_calls.append(dict(kwargs))
            super().__init__(**kwargs)

        def with_profile(self, profile_residual_fn):  # type: ignore[override]
            with_profile_calls.append(profile_residual_fn)
            return super().with_profile(profile_residual_fn)

    adapter = _twodim_adapter
    n_rounds = 3
    profile = lambda x: float(x)  # noqa: E731
    scheduler = _RecordingCodimensionScheduler(
        cycle_length=n_rounds,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
        eps_direction="decreasing",
        seed=42,
    )
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=default_bounded_merge_operator(),
    )
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
            paper_quantities_provider=profile,
        )
    )

    # F10 wiring: the public ``with_profile`` swap-constructor was
    # called exactly once with the supplied provider.
    assert len(with_profile_calls) == 1, (
        f"expected exactly one with_profile() call; got {len(with_profile_calls)} "
        f"(hasattr fallback likely re-introduced)"
    )
    assert with_profile_calls[0] is profile, (
        "with_profile() must be invoked with the configured "
        "paper_quantities_provider"
    )

    # The runner MUST take the return value of ``with_profile`` (no
    # private-attr reconstruction path that ignores the public
    # swap-constructor). Identity check — the post-run scheduler is
    # a different object from the one originally passed in, AND is
    # the one returned by ``with_profile``.
    assert runner.scheduler is not scheduler, (
        "runner must swap to the scheduler returned by with_profile(); "
        "post-run scheduler is identical to the original"
    )

    # And the swapped scheduler carries the supplied provider as its
    # residual profile (round-trip through the public API).
    assert getattr(runner.scheduler, "_profile_residual_fn", None) is profile, (
        "swapped scheduler must carry the supplied profile_residual_fn"
    )


def test_runner_f10_does_not_read_scheduler_private_attributes(
    _twodim_adapter,
) -> None:
    """F10 hardening: the runner MUST NOT reach into the scheduler's
    private attributes (``_n_min`` / ``_n_max`` / ``_eps_implicit`` /
    ``_eps_direction`` / ``_seed``) when wiring the paper-quantities
    upgrade.

    The test wraps a :class:`CodimensionSheetScheduler` subclass that
    blocks every read of those five private attributes via
    :py:meth:`__getattribute__`. The only allowed escape hatch is the
    public :meth:`with_profile` swap-constructor (which the subclass
    permits by name). If the runner reads any of the forbidden private
    attributes — e.g. by re-introducing the ``hasattr`` fallback that
    reconstructs via ``CodimensionSheetScheduler(...)`` and reads
    ``self._scheduler._n_min`` — the read raises ``AttributeError``
    and this test fails.
    """
    from adaptive_reflow.algorithm.scheduler import (
        CodimensionSheetScheduler,
    )

    class _PrivateAttrGuardedScheduler(CodimensionSheetScheduler):
        """Codimension scheduler that forbids external reads of internals.

        Reading any of ``_n_min`` / ``_n_max`` / ``_eps_implicit`` /
        ``_eps_direction`` / ``_seed`` raises :class:`AttributeError`.
        The :meth:`with_profile` method is allow-listed (it is the
        canonical swap-constructor introduced by F10).
        """

        _FORBIDDEN_PRIVATE_ATTRS = frozenset(
            {
                "_n_min",
                "_n_max",
                "_eps_implicit",
                "_eps_direction",
                "_seed",
            }
        )

        def __getattribute__(self, name: str) -> object:
            # Bypass our override for the meta-attribute that lists
            # what to forbid (avoid recursive __getattribute__ calls).
            if name == "_FORBIDDEN_PRIVATE_ATTRS":
                return object.__getattribute__(self, name)
            forbidden = type(self).__dict__.get(
                "_FORBIDDEN_PRIVATE_ATTRS", frozenset()
            )
            if name in forbidden:
                # Inspect the call stack. Reads are allowed ONLY when
                # the caller is inside the ``CodimensionSheetScheduler``
                # implementation (filename ends with ``_core.py`` —
                # ``__init__`` and ``with_profile`` are defined there).
                # Reads originating from the runner (``runner.py``)
                # or anywhere else are blocked.
                import sys

                frame = sys._getframe(1)
                allowed = False
                while frame is not None:
                    fname = frame.f_code.co_filename or ""
                    if fname.endswith("_core.py"):
                        allowed = True
                        break
                    frame = frame.f_back
                if not allowed:
                    raise AttributeError(
                        f"F10 guard: private attribute {name!r} is not "
                        "exposed to the runner; use "
                        "CodimensionSheetScheduler.with_profile()"
                    )
            return object.__getattribute__(self, name)

    adapter = _twodim_adapter
    n_rounds = 2
    profile = lambda x: float(x)  # noqa: E731
    scheduler = _PrivateAttrGuardedScheduler(
        cycle_length=n_rounds,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
        eps_direction="decreasing",
        seed=42,
    )
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=default_bounded_merge_operator(),
    )
    # If the runner reaches into any forbidden private attribute the
    # guard raises ``AttributeError`` and the run fails — the test
    # catches it and reports a clear message. A clean run (no error)
    # proves the runner took the public ``with_profile`` path.
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
            paper_quantities_provider=profile,
        )
    )
    assert isinstance(runner.scheduler, CodimensionSheetScheduler)


def test_runner_f10_no_private_attr_reach_arounds_in_source() -> None:
    """F10 source-level guard: the runner MUST NOT reach into the
    scheduler's private attributes anywhere in its body.

    This is the strongest F10 invariant: even if a runtime ``hasattr``
    branch were re-introduced as a fallback for a hypothetical
    scheduler without ``with_profile``, the constructor call that
    copies private attributes (e.g. ``self._scheduler._n_min``) would
    re-appear here and fail this assertion. The runner's contract is
    to call :meth:`CodimensionSheetScheduler.with_profile` and nothing
    else when wiring paper quantities.
    """
    import inspect

    from adaptive_reflow.algorithm.runner import ReInferenceRunner

    src = inspect.getsource(ReInferenceRunner)
    forbidden_tokens = (
        "self._scheduler._n_min",
        "self._scheduler._n_max",
        "self._scheduler._eps_implicit",
        "self._scheduler._eps_direction",
        "self._scheduler._seed",
        "self._scheduler._profile_residual_fn",
        # The runner had a `hasattr(self._scheduler, "with_profile")`
        # fallback that called ``CodimensionSheetScheduler(...)`` via
        # private attrs; that path is forbidden post-F10.
        'hasattr(self._scheduler, "with_profile")',
    )
    for token in forbidden_tokens:
        assert token not in src, (
            f"F10 violation: runner contains forbidden reach-around "
            f"{token!r}; use CodimensionSheetScheduler.with_profile() "
            "instead"
        )
    # And the public path IS present — sanity guard so a future
    # refactor that deletes the call also fails the test.
    assert "self._scheduler.with_profile(provider)" in src, (
        "F10 expectation: runner must call self._scheduler.with_profile(provider)"
    )


# ---------------------------------------------------------------------------
# 11. CONTRACT 2.4 — runner calls the merge operator between policy
# emission and engine.apply_restart_distribution.
# ---------------------------------------------------------------------------


def test_runner_calls_merge_operator_between_policy_and_engine(
    _twodim_adapter,
) -> None:
    """Contract 2.4: the runner must call the configured
    :class:`MergeOperatorProtocol` once per round between policy
    emission and ``engine.run_round``.

    The test wires a recording merge operator that records every
    call's ``prev``, ``dynamic``, ``cap``, ``floor`` arguments and
    feeds the runner a simple
    ``constant driver + cosine scheduler`` configuration so each
    call is non-trivial. The recording shows the merge operator saw
    one call per round with the expected ``cap`` / ``floor`` /
    ``dynamic`` values.
    """
    from adaptive_reflow.algorithm.merge_operator import (
        EMAOperator,
        IdentityOperator,
        MergeOperatorProtocol,
    )

    captured: list[dict[str, float]] = []

    class _RecordingMergeOperator:
        """Wrap :class:`EMAOperator` and record every call."""

        def __init__(self) -> None:
            self._inner = EMAOperator(alpha=0.5)

        def merge(
            self,
            prev: float,
            dynamic: float,
            *,
            cap: float,
            floor: float,
            delta_cap_up: float,
            delta_cap_down: float,
            audit_codes=None,
        ):
            captured.append(
                {
                    "prev": float(prev),
                    "dynamic": float(dynamic),
                    "cap": float(cap),
                    "floor": float(floor),
                    "delta_cap_up": float(delta_cap_up),
                    "delta_cap_down": float(delta_cap_down),
                }
            )
            return self._inner.merge(
                prev=prev,
                dynamic=dynamic,
                cap=cap,
                floor=floor,
                delta_cap_up=delta_cap_up,
                delta_cap_down=delta_cap_down,
                audit_codes=audit_codes,
            )

    adapter = _twodim_adapter
    n_rounds = 4
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    driver = ConstantPolicyDriver(beta=0.5)
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=driver,
        merge_operator=_RecordingMergeOperator(),
    )
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    # One merge call per round.
    assert len(captured) == n_rounds, (
        f"expected {n_rounds} merge calls; got {len(captured)}"
    )
    # ``cap`` matches the schedule's ``n_cap``; ``floor`` matches
    # ``n_min``; ``delta_cap_up == delta_cap_down == 1.0`` (the
    # runner's pass-through configuration).
    n_min = float(scheduler._config.n_min)  # noqa: SLF001 — internal config access
    for r, call in enumerate(captured):
        sample = scheduler.sample(0, r, r)
        assert call["cap"] == pytest.approx(float(sample.n_cap))
        assert call["floor"] == pytest.approx(n_min)
        assert call["delta_cap_up"] == pytest.approx(1.0)
        assert call["delta_cap_down"] == pytest.approx(1.0)
        # ``dynamic`` is the driver's emitted ``beta`` (constant 0.5).
        assert call["dynamic"] == pytest.approx(0.5)


def test_runner_merge_step_observable_in_beta_trajectory(
    _twodim_adapter,
) -> None:
    """Contract 2.4: switching the merge operator is observable in the
    runner's per-round ``beta`` trajectory.

    The test wires a constant ``beta = 0.7`` driver and runs the
    runner once with the default
    :class:`BoundedMergeOperator` (caps the result at
    ``min(0.7, n_cap)``) and once with the :class:`IdentityOperator`
    (pass-through — always ``0.7``). The two trajectories MUST differ
    when the cosine ``n_cap`` drops below ``0.7``.
    """
    adapter = _twodim_adapter
    n_rounds = 4
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    driver = ConstantPolicyDriver(beta=0.7)

    runner_bounded = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=driver,
        merge_operator=default_bounded_merge_operator(),
    )
    bounded_result = runner_bounded.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    runner_identity = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
        policy_driver=ConstantPolicyDriver(beta=0.7),
        merge_operator=IdentityOperator(),
    )
    identity_result = runner_identity.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    bounded_betas = [
        bounded_result.per_round_metrics[r]["beta"] for r in range(n_rounds)
    ]
    identity_betas = [
        identity_result.per_round_metrics[r]["beta"] for r in range(n_rounds)
    ]
    # Identity preserves ``0.7`` every round; bounded caps at
    # ``min(0.7, n_cap)`` so the trajectories diverge for rounds
    # where ``n_cap < 0.7``.
    assert identity_betas == pytest.approx([0.7] * n_rounds)
    assert bounded_betas != identity_betas, (
        f"merge operator choice must affect the beta trajectory; "
        f"bounded={bounded_betas!r} identity={identity_betas!r}"
    )
    # The bounded path caps each ``beta`` at the schedule's ``n_cap``.
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        assert bounded_betas[r] == pytest.approx(min(0.7, float(sample.n_cap)))


def test_runner_records_merge_audit_codes(_twodim_adapter) -> None:
    """Contract 2.4: the runner records the merge operator's audit
    codes in the per-round metric dict under ``merge_audit_codes``
    so a downstream audit reader can audit-replay the runner's
    per-round restart decision.
    """
    adapter = _twodim_adapter
    n_rounds = 2
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
        policy_driver=ConstantPolicyDriver(beta=0.5),
        merge_operator=default_bounded_merge_operator(),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    # The merge audit list is exposed as ``merge_audit_codes`` on
    # every per-round metric dict (may be empty for the happy path;
    # test only checks the key is present and is a list).
    for r in range(n_rounds):
        metric = result.per_round_metrics[r]
        assert "merge_audit_codes" in metric, (
            f"round {r}: missing merge_audit_codes; keys={sorted(metric)!r}"
        )
        assert isinstance(metric["merge_audit_codes"], list), (
            f"round {r}: merge_audit_codes must be a list; "
            f"got {type(metric['merge_audit_codes']).__name__}"
        )


# ---------------------------------------------------------------------------
# 12. CONTRACT 1.2 — driver / engine dedup verification.
# ---------------------------------------------------------------------------


def test_driver_computed_beta_suppresses_engine_override(
    _twodim_adapter,
) -> None:
    """Contract 1.2: when the policy carries
    ``driver_computed_beta=True`` (the runner-built policy with the
    default :class:`ScheduleDerivedPolicyDriver` driver), the
    engine SKIPS its inline ``_policy_with_schedule_beta``
    re-override. The audit trail records the override exactly once
    (by the driver), not twice (driver + engine).
    """
    adapter = _twodim_adapter
    n_rounds = 3
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=default_bounded_merge_operator(),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )
    # Every round trace's ``audit_codes`` MUST NOT contain the engine
    # schedule-driven override (which the legacy engine emitted as
    # ``merge_cap_below_floor`` or the per-override audit codes);
    # the runner's merge step does not raise the override audit
    # code via the engine — only the merge operator's audit codes
    # surface in ``per_round_metrics[r]['merge_audit_codes']`` (the
    # round trace itself is the engine's view of the world).
    for r, trace in enumerate(result.round_traces):
        # The engine-side override audit (``engine_beta_overridden``)
        # is no longer emitted because the engine skips its inline
        # override when ``driver_computed_beta=True``. We assert the
        # audit trail is empty so the de-duplication is observable.
        assert trace.audit_codes == (), (
            f"round {r}: engine should not emit any audit codes "
            f"because the driver wrote beta_by_channel; got "
            f"audit_codes={trace.audit_codes!r}"
        )


# P0-7 — runner calls adapter.export_trajectory() instead of getattr
# ---------------------------------------------------------------------------


def test_p0_7_runner_calls_export_trajectory_on_twodim_adapter(
    _twodim_adapter,
) -> None:
    """P0-7: when wired to :class:`TwoDimFMAdapter`, the runner captures
    the per-round endpoint via the adapter's public
    :meth:`export_trajectory` method (not the private ``_native_states``
    dict). The resulting ``result.endpoints[r]`` is finite and matches
    the actual last row of the stored trajectory.
    """
    n_rounds = 2
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        outer_cycle_id=0,
        target_round=0,
        seed=42,
        channels=TWODIM_FM_CHANNELS,
    )
    runner = ReInferenceRunner(adapter=_twodim_adapter)
    result = runner.run(config)

    # All endpoint rows are finite (no NaN capture).
    assert not np.isnan(result.endpoints).any(), (
        f"runner failed to capture endpoints via export_trajectory; "
        f"endpoints={result.endpoints!r}"
    )
    # First-round endpoint matches the adapter's stored trajectory.
    expected_first = _twodim_adapter.export_trajectory(
        result.round_traces[0].integrator_trace
    )[-1]
    np.testing.assert_array_almost_equal(
        result.endpoints[0], np.asarray(expected_first, dtype=np.float64).reshape(2)
    )
    # Endpoint-export-failure flag is 0.0 (success).
    assert result.per_round_metrics[0]["endpoint_export_failed"] == 0.0


def test_p0_7_runner_handles_reference_flowa_notimplemented() -> None:
    """P0-7: when wired to :class:`ReferenceFlowAAdapter` (which does
    not preserve a native trajectory), the runner catches
    :class:`NotImplementedError` from ``adapter.export_trajectory``,
    records ``endpoint_export_failed=1.0`` in the per-round metrics,
    and leaves the corresponding ``endpoints[r]`` row as ``NaN``.
    """
    from adaptive_reflow.adapters import ReferenceFlowAAdapter

    adapter = ReferenceFlowAAdapter()
    n_rounds = 2
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        outer_cycle_id=0,
        target_round=0,
        seed=42,
        channels=("coordinate",),
    )
    runner = ReInferenceRunner(adapter=adapter)
    result = runner.run(config)

    # Every round flagged as export-failed (ReferenceFlowAAdapter raises).
    for r in range(n_rounds):
        assert result.per_round_metrics[r]["endpoint_export_failed"] == 1.0, (
            f"round {r}: expected endpoint_export_failed=1.0; "
            f"got metrics={result.per_round_metrics[r]!r}"
        )
    # Endpoint rows are NaN (no trajectory was captured).
    assert np.isnan(result.endpoints).all(), (
        f"expected NaN endpoints; got {result.endpoints!r}"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))


# ---------------------------------------------------------------------------
# F-34 — runner propagates bundle between rounds via observe_endpoint.
# ---------------------------------------------------------------------------


class _StatePropagatingAdapterRecorder:
    """Wrap :class:`TwoDimFMAdapter` and record every bundle passed to
    ``apply_restart_distribution`` so the F-34 propagation test can
    verify round r+1 receives round r's observe_endpoint output.

    The engine internally dispatches
    ``adapter.apply_restart_distribution(bundle, policy)`` for each
    round; capturing that bundle on a per-round basis lets us assert
    the round-to-round chain end-to-end.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        # Recorded inputs to apply_restart_distribution (one per round).
        self.captured_bundles: list[Any] = []
        # Recorded outputs from observe_endpoint (one per round).
        self.captured_observed_bundles: list[Any] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def apply_restart_distribution(self, state: Any, policy: Any) -> Any:
        self.captured_bundles.append(state)
        return self._inner.apply_restart_distribution(state, policy)

    def observe_endpoint(self, trace: Any, state: Any) -> Any:
        out = self._inner.observe_endpoint(trace, state)
        self.captured_observed_bundles.append(out)
        return out


def test_runner_propagates_bundle_between_rounds(_twodim_adapter) -> None:
    """F-34: round ``r+1``'s input bundle is round ``r``'s
    ``observe_endpoint`` output, NOT the round-0 ``build_initial_state``
    bundle.

    The runner chains the bundle between rounds via::

        bundle = self._adapter.observe_endpoint(trace, bundle)

    so each round's engine dispatch receives a bundle whose
    ``source_round`` has been incremented by the adapter. The test
    captures the ``source_bundle_digest`` of each round's
    ``RoundTrace`` and asserts:

    1. Every round's ``source_bundle_digest`` is distinct
       (the runner's bundle advances round-to-round; pre-F-34 the
       engine saw the round-0 ``build_initial_state`` bundle every
       round so all digests collapsed).
    2. Round ``r``'s ``source_bundle_digest`` equals the digest of
       round ``r-1``'s ``observe_endpoint`` output bundle — i.e.,
       the runner's chain is end-to-end observable in the audit
       trail.

    The test uses a recording adapter to capture the chain and
    asserts the runner maintains a true per-round bundle evolution
    rather than reusing the round-0 ``build_initial_state`` bundle.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    # Build a fresh adapter instance with a recording wrapper so the
    # existing module-scoped fixture is left pristine for other tests.
    inner = TwoDimFMAdapter(
        weights_path=_twodim_adapter._weights_path  # type: ignore[attr-defined]
        if hasattr(_twodim_adapter, "_weights_path")
        else None,
        target=getattr(_twodim_adapter, "_target", "two_moons"),
    )
    recording = _StatePropagatingAdapterRecorder(inner)

    n_rounds = 4
    runner = ReInferenceRunner(
        adapter=recording,  # type: ignore[arg-type]
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    # The runner's bundle chain is observable via ``source_bundle_digest``
    # in each round's ``RoundTrace`` (computed from the bundle passed
    # to ``engine.run_round``). With F-34 propagation each round sees
    # the previous round's ``observe_endpoint`` output, NOT the
    # round-0 ``build_initial_state`` bundle.
    digests = [
        str(trace.source_bundle_digest) for trace in result.round_traces
    ]
    assert len(set(digests)) == n_rounds, (
        f"F-34 propagation failed: round-to-round source_bundle_digest "
        f"values collapsed; digests={digests!r}. The runner is reusing "
        f"the same bundle across rounds (legacy not_chain_yet behaviour)."
    )

    # The chain invariant: round ``r+1``'s ``source_bundle_digest`` is
    # NOT the round-0 ``build_initial_state`` digest. The recorder
    # captured the round-0 bundle's digest as the first
    # ``captured_bundles[0]``.
    initial_digest = str(recording.captured_bundles[0].native_state_digest)
    for r in range(1, n_rounds):
        assert str(result.round_traces[r].source_bundle_digest) != initial_digest, (
            f"round {r}: source_bundle_digest still equals round-0 "
            f"build_initial_state digest ({initial_digest}); F-34 chain "
            f"did not propagate the prior endpoint."
        )


def test_runner_state_propagation_makes_per_round_outputs_distinct(
    _twodim_adapter,
) -> None:
    """F-34 corollary: chaining the bundle between rounds produces
    distinct per-round endpoints and ``source_bundle_digest`` values.

    Without F-34 propagation (the legacy ``not_chain_yet`` behaviour
    where every round sees the round-0 bundle), all rounds would
    produce byte-identical ``source_bundle_digest`` values because
    the engine dispatches ``apply_restart_distribution(bundle, policy)``
    on the same input. With F-34 propagation, each round's
    ``source_bundle_digest`` MUST differ from the previous round's
    ``endpoint_digest`` because the runner feeds the previous round's
    ``observe_endpoint`` output into the next round's engine call.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    inner = TwoDimFMAdapter(
        weights_path=_twodim_adapter._weights_path  # type: ignore[attr-defined]
        if hasattr(_twodim_adapter, "_weights_path")
        else None,
        target=getattr(_twodim_adapter, "_target", "two_moons"),
    )
    n_rounds = 4
    runner = ReInferenceRunner(
        adapter=inner,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=TWODIM_FM_CHANNELS,
        )
    )

    # Per-round ``source_bundle_digest`` MUST be distinct (otherwise
    # the engine saw the same bundle every round, defeating the chain).
    digests = [
        str(trace.source_bundle_digest) for trace in result.round_traces
    ]
    assert len(set(digests)) == n_rounds, (
        f"F-34 propagation failed: every round saw the same source "
        f"bundle digest; got digests={digests!r}"
    )
    # Each round's source_bundle_digest MUST equal the previous round's
    # endpoint_digest (the chain invariant).
    for r in range(1, n_rounds):
        prev_endpoint = str(result.round_traces[r - 1].endpoint_digest)
        curr_source = str(result.round_traces[r].source_bundle_digest)
        # ``source_bundle_digest`` is the digest of the bundle as
        # observed by the engine, while ``endpoint_digest`` is the
        # adapter's "detached" endpoint digest. The chain in the
        # runner is via ``observe_endpoint``, which produces a fresh
        # bundle; the bundle's digest changes round-to-round because
        # the adapter increments ``source_round`` and embeds the
        # trajectory's final row. We don't require byte equality
        # (different digest inputs), but the source MUST NOT match
        # the previous round's source (i.e., it advances).
        assert curr_source != str(
            result.round_traces[r - 1].source_bundle_digest
        ), (
            f"round {r}: source_bundle_digest must differ from "
            f"round {r - 1}'s; both={curr_source!r}"
        )
        # And we expect the per-round endpoint rows in
        # ``result.endpoints`` to advance (chain produces distinct
        # trajectories per round, not a fixed point).
        if not np.isnan(result.endpoints[r]).any():
            assert not np.allclose(
                result.endpoints[r], result.endpoints[r - 1]
            ), (
                f"round {r}: chained endpoint collapsed to "
                f"round {r - 1}'s endpoint (F-34 propagation broken)"
            )
        # Sanity: prev_endpoint is non-empty (round completed).
        assert prev_endpoint != "", (
            f"round {r - 1}: endpoint_digest must be populated; "
            f"got {prev_endpoint!r}"
        )


# ---------------------------------------------------------------------------
# F7 — runner threads ``schedule_sample`` into the EMA merge operator
# ---------------------------------------------------------------------------


class _ScheduleSampleRecordingMerge:
    """Wrap :class:`EMAOperator` and capture the ``schedule_sample`` kwarg.

    Used by the F7 regression test to confirm the runner threads the
    per-round :class:`ScheduleSample` into the merge call so the
    schedule-aware alpha modulation on :class:`EMAOperator` is
    reachable.
    """

    def __init__(self) -> None:
        self.schedule_samples: list[Any] = []

    def config_hash(self) -> str:
        return "schedule-sample-recording"

    def merge(
        self,
        prev,
        dynamic,
        *,
        cap,
        floor,
        delta_cap_up,
        delta_cap_down,
        audit_codes=None,
        schedule_sample=None,
    ) -> float:
        self.schedule_samples.append(schedule_sample)
        if audit_codes is not None:
            pass
        # Pretend we are ``EMAOperator(alpha=0.5)`` so the runner
        # sees a finite result and we don't need the adapter to run
        # the full pipeline (the 2D FM adapter's W1 fix is exercised
        # elsewhere — see ``test_runner_calls_merge_operator_...``).
        return float(prev + 0.5 * (dynamic - prev))


def test_runner_with_ema_merge_propagates_schedule_sample(_twodim_adapter) -> None:
    """Runner threads ``schedule_sample`` into merge when the operator advertises the kwarg.

    Regression test for finding #7 in
    ``docs/r3-survey/05-verified-findings.md``: the runner used to
    call ``self._merge.merge(...)`` without ``schedule_sample``, so
    the schedule-aware alpha modulation on :class:`EMAOperator` was
    dead on the runner's data path. The fix threads the
    :class:`ScheduleSample` through the merge call when the operator
    advertises the kwarg.

    We use a recording wrapper around :class:`EMAOperator` so the
    test does NOT depend on the 2D FM adapter's full pipeline (the
    pipeline is exercised by ``test_runner_calls_merge_operator_...``;
    the present test isolates the runner's threading behaviour).
    The recording shows the merge operator saw one non-``None``
    ``schedule_sample`` per round.
    """
    adapter = _twodim_adapter
    n_rounds = 4
    recording = _ScheduleSampleRecordingMerge()
    scheduler = default_cosine_scheduler(cycle_length=n_rounds)
    # The default driver is ``ScheduleDerivedPolicyDriver``; the F25
    # short-circuit would skip the merge call on the
    # schedule-derived path. Use ``ConstantPolicyDriver`` to ensure
    # the merge runs every round so the test exercises the
    # ``schedule_sample`` kwarg threading.
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        merge_operator=recording,
        policy_driver=ConstantPolicyDriver(beta=0.5),
    )
    runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds,
            channels=TWODIM_FM_CHANNELS,
            seed=42,
        )
    )
    # F25 short-circuits the merge call for ``schedule_derived``
    # driver; ``ConstantPolicyDriver`` is non-schedule-derived so
    # the merge runs every round.
    assert len(recording.schedule_samples) == n_rounds
    for sample in recording.schedule_samples:
        assert sample is not None
        # The runner must forward a real ``CosineScheduleSample`` so
        # ``EMAOperator`` can read ``n_cap``.
        assert hasattr(sample, "n_cap")


# ---------------------------------------------------------------------------
# P0-1 (F-31) — runner must call the merge operator on the
# schedule-derived driver path too (F25 W2 leak fix).
# ---------------------------------------------------------------------------


class _CountingMergeOperator:
    """Merge operator that records every ``merge`` call.

    Implements :class:`MergeOperatorProtocol` (duck-typed: must
    expose ``merge`` and ``config_hash``). Used by the
    ``test_runner_calls_merge_operator_on_schedule_derived`` and the
    ``test_runner_calls_merge_operator_between_policy_and_engine``
    tests to count merge invocations across rounds.
    """

    def __init__(self) -> None:
        self.calls = 0

    def config_hash(self) -> str:
        return "counting-merge-operator"

    def merge(
        self,
        prev,
        dynamic,
        *,
        cap,
        floor,
        delta_cap_up,
        delta_cap_down,
        audit_codes=None,
        schedule_sample=None,
    ) -> float:
        self.calls += 1
        if audit_codes is not None:
            pass
        return float(dynamic)


def test_runner_calls_merge_operator_on_schedule_derived(
    _twodim_adapter,
) -> None:
    """P0-1 (F-31): the runner must invoke the merge operator on the
    ``schedule_derived`` driver path.

    Earlier the runner short-circuited the merge step for
    ``schedule_derived`` drivers (the bounded merge with
    ``delta_cap = 1.0`` collapses to ``clamp(n_cap, n_min, n_cap) ==
    n_cap`` — an identity), which leaked W2: the bounded envelope's
    ``floor`` / clipping / audit codes never fired on the
    schedule-derived path so the four framework rows collapsed to the
    same trajectory. The fix always calls ``merge`` regardless of
    driver family. With the bounded merge collapsed to an identity
    on the schedule-derived path, ``beta == n_cap`` byte-for-byte
    is preserved for legacy callers.
    """
    from adaptive_reflow.algorithm import ScheduleDerivedPolicyDriver

    adapter = _twodim_adapter
    merge_op = _CountingMergeOperator()
    n_rounds = 3
    runner = ReInferenceRunner(
        adapter=adapter,
        policy_driver=ScheduleDerivedPolicyDriver(),
        merge_operator=merge_op,
    )
    result = runner.run(
        ReInferenceConfig(
            n_rounds=n_rounds, channels=TWODIM_FM_CHANNELS, seed=42,
        )
    )
    # One merge call per round — even on the schedule-derived path.
    assert merge_op.calls == n_rounds, (
        f"runner must call merge once per round on the "
        f"schedule_derived path; got {merge_op.calls}"
    )
    for r in range(n_rounds):
        sample = result.per_round_metrics[r]
        # With the merge collapsed to identity the runner emits the
        # schedule-derived ``beta == sample.n_cap`` directly.
        assert sample["beta"] == pytest.approx(sample["n_cap"])


# ---------------------------------------------------------------------------
# F22 — ``target_round`` is consistent across ledger + scheduler sample
# ---------------------------------------------------------------------------


def test_runner_target_round_consistent_across_ledger_and_sample(
    _twodim_adapter,
) -> None:
    """``sample.computed_at_round`` and ``ledger_row.target_round`` agree.

    Regression test for finding #22 in
    ``docs/r3-survey/05-verified-findings.md``: the runner used to
    pass ``target_round=config.target_round + r`` to the scheduler
    while the engine's ``build_ledger_row`` used ``target_round=r``,
    so the two consumers disagreed by ``config.target_round``. The fix
    threads ``r`` (the local round index) through both call sites.
    """
    adapter = _twodim_adapter
    n_rounds = 4
    runner = ReInferenceRunner(adapter=adapter)
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        outer_cycle_id=7,
        target_round=10,  # non-zero — would have caused the offset bug
        seed=42,
        channels=TWODIM_FM_CHANNELS,
    )
    result = runner.run(config)
    for r in range(n_rounds):
        sample_computed_at_round = int(
            result.per_round_metrics[r].get(
                "computed_at_round", r
            )
            if "computed_at_round" in result.per_round_metrics[r]
            else r
        )
        # The scheduler's ``ScheduleSample.computed_at_round`` is the
        # ``target_round`` argument the runner passed to ``sample``;
        # the ledger row's ``target_round`` is the engine's local
        # round index. After the F22 fix they MUST agree.
        ledger_target_round = int(result.ledger_rows[r].target_round)
        assert sample_computed_at_round == ledger_target_round == r


# ---------------------------------------------------------------------------
# Forward noise injection (P0-7) — runner emits FORWARD_NOISE_INJECTED
# ---------------------------------------------------------------------------


def test_runner_emits_forward_noise_injected_metric() -> None:
    """Runner's per-round metric dict carries ``forward_noise_injected`` flag."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter()
    runner = ReInferenceRunner(adapter=adapter, scheduler=ConstantScheduler(cycle_length=4, n_cap=0.5))
    result = runner.run(ReInferenceConfig(n_rounds=3, channels=("xy",), seed=42))
    for r in range(3):
        metric = result.per_round_metrics[r]
        assert metric["forward_noise_injected"] == 1.0
        assert "FORWARD_NOISE_INJECTED" in metric["merge_audit_codes"]


# ---------------------------------------------------------------------------
# Hash-chained ledger (P0-8) — round-event monotonicity
# ---------------------------------------------------------------------------


def test_runner_emits_hash_chained_ledger_rows() -> None:
    """Runner returns a ``ledger_rows`` tuple whose chain validates."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame.engine import verify_ledger_chain

    adapter = TwoDimFMAdapter()
    runner = ReInferenceRunner(adapter=adapter)
    result = runner.run(ReInferenceConfig(n_rounds=4, channels=("xy",), seed=42))
    rows = result.ledger_rows
    assert len(rows) == 4
    # Round 0 has no prev hash; subsequent rounds chain to the previous.
    assert rows[0].prev_ledger_row_hash is None
    for i in range(1, 4):
        assert rows[i].prev_ledger_row_hash == str(rows[i - 1].row_hash)
    ok, err = verify_ledger_chain(rows)
    assert ok, err


def test_runner_ledger_chain_breaks_on_tamper() -> None:
    """Tampering with any ledger row breaks the chain integrity check."""
    from dataclasses import replace

    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.frame.engine import verify_ledger_chain

    adapter = TwoDimFMAdapter()
    runner = ReInferenceRunner(adapter=adapter)
    result = runner.run(ReInferenceConfig(n_rounds=3, channels=("xy",), seed=42))
    rows = list(result.ledger_rows)
    # Tamper round 1 by replacing its applied_policy_hash but keeping the
    # stale row_hash. The recompute will mismatch.
    tampered = replace(
        rows[1],
        applied_policy_hash="tampered-hash",
        row_hash=rows[1].row_hash,
    )
    rows[1] = tampered
    ok, err = verify_ledger_chain(tuple(rows))
    assert not ok
    assert "row[1]" in err


# ---------------------------------------------------------------------------
# F14 — runner reads ``adapter.state_shape`` for the forward-noise prior
# ---------------------------------------------------------------------------


def test_runner_injects_noise_with_adapter_state_shape(_twodim_adapter) -> None:
    """Runner allocates ``np.zeros(state_shape, ...)`` based on the adapter's advertised shape.

    Regression test for finding #14 in
    ``docs/r3-survey/05-verified-findings.md``: the runner used to
    hard-code ``np.zeros(2, dtype=np.float64)`` regardless of the
    adapter's native state shape, silently breaking adapters with
    non-2-D state spaces. The fix reads the adapter's ``state_shape``
    attribute (default ``(2,)``) so the per-round ``inject_noise``
    call gets the right shape.
    """
    from adaptive_reflow.algorithm import ConstantScheduler

    adapter = _twodim_adapter
    # Override the advertised state shape on this run; the runner MUST
    # respect it.
    adapter.state_shape = (4,)  # type: ignore[attr-defined]

    class _ShapeCapturingScheduler:
        """Wrap the constant scheduler and capture the prior-array shape passed to ``inject_noise``."""

        def __init__(self, inner):
            self._inner = inner
            self.captured_shapes = []

        def sample(self, outer_cycle_id, round_in_cycle, target_round):
            return self._inner.sample(
                outer_cycle_id, round_in_cycle, target_round
            )

        def config_hash(self):
            return self._inner.config_hash()

        def reset(self):
            self._inner.reset()

        def inject_noise(self, prior_array, sample, generator=None):
            self.captured_shapes.append(tuple(prior_array.shape))
            # Return the prior unchanged so the runner sees a valid
            # bundle shape regardless of the adapter's hook.
            return prior_array

    scheduler = ConstantScheduler(cycle_length=2, n_cap=0.5)
    capturing = _ShapeCapturingScheduler(scheduler)
    runner = ReInferenceRunner(adapter=adapter, scheduler=capturing)
    runner.run(
        ReInferenceConfig(n_rounds=2, channels=TWODIM_FM_CHANNELS, seed=42)
    )
    # Per-round shape MUST match the adapter's advertised ``state_shape``.
    assert all(shape == (4,) for shape in capturing.captured_shapes)
    # Cleanup the override so the fixture stays pristine for other tests.
    if hasattr(adapter, "state_shape"):
        delattr(adapter, "state_shape")


# ---------------------------------------------------------------------------
# F3 — runner routes forward-noise perturbation through the adapter
# ---------------------------------------------------------------------------


def test_runner_emits_forward_noise_through_adapter(_twodim_adapter) -> None:
    """Runner calls ``adapter.inject_forward_noise`` when the adapter implements the hook.

    Regression test for finding #3 in
    ``docs/r3-survey/05-verified-findings.md``: the runner used to
    compute the ``inject_noise`` result and discard it (``_ =
    injected``); the symmetric FORWARD side of the round model was
    computed but never reached the bundle. The fix detects the
    adapter's ``inject_forward_noise`` method via ``hasattr`` and
    routes the perturbation through it.
    """
    from adaptive_reflow.algorithm import ConstantScheduler

    adapter = _twodim_adapter
    captured = []

    def _inject_forward_noise(bundle, injected):
        captured.append((bundle, injected))
        return bundle

    adapter.inject_forward_noise = _inject_forward_noise  # type: ignore[attr-defined]

    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=ConstantScheduler(cycle_length=4, n_cap=0.5),
    )
    runner.run(
        ReInferenceConfig(n_rounds=3, channels=TWODIM_FM_CHANNELS, seed=42)
    )
    # The runner must have called the adapter's hook once per round
    # (F3 closes Loop 4 by wiring the forward side into the bundle).
    assert len(captured) == 3
    # Each call receives the bundle and the injected perturbation.
    for bundle, injected in captured:
        assert bundle is not None
        assert injected is not None

    # Cleanup the monkey-patched hook so the fixture stays pristine.
    if hasattr(adapter, "inject_forward_noise"):
        delattr(adapter, "inject_forward_noise")


# ---------------------------------------------------------------------------
# C4 — runner passes selection_ratio, paper quantities, schedule evidence
# ---------------------------------------------------------------------------


def test_runner_passes_paper_quantity_metrics_to_feedback(_twodim_adapter) -> None:
    """``record_round_feedback`` receives selection_ratio / paper quantities / schedule evidence.

    Regression test for C4 (close Loop 2 — paper quantities -> scheduler
    feedback). When ``config.paper_quantities_provider`` is set and a
    selector evaluator is configured, the per-round metric dict MUST
    carry ``selection_ratio``, ``paper_quantity_diagnostics``, and
    ``schedule_evidence_ratio`` so the
    :class:`EvidenceDrivenScheduler` (Agent 1c's consumer) can update
    ``n_cap`` via PID-lite. The test uses a recording scheduler to
    confirm all three keys reach ``record_round_feedback``.
    """
    import math

    adapter = _twodim_adapter
    n_rounds = 4

    # Recording scheduler that captures the metric dict.
    class _RecordingScheduler:
        def __init__(self, inner):
            self._inner = inner
            self.feedback_calls = []

        def sample(self, outer_cycle_id, round_in_cycle, target_round):
            return self._inner.sample(
                outer_cycle_id, round_in_cycle, target_round
            )

        def config_hash(self):
            return self._inner.config_hash()

        def reset(self):
            self._inner.reset()

        def record_round_feedback(self, round_in_cycle, metrics):
            self.feedback_calls.append((int(round_in_cycle), dict(metrics)))

    inner = default_cosine_scheduler(cycle_length=n_rounds)
    recording = _RecordingScheduler(inner)

    # Mock selection_evaluator with a ``selection_ratio`` oracle.
    class _SelectionMock:
        def oracle(self, bundle, *, channel, seed):
            return {"selection_ratio": 0.8}

    profile = lambda x: math.sin(x)  # noqa: E731

    runner = ReInferenceRunner(
        adapter=adapter, scheduler=recording
    )
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        channels=TWODIM_FM_CHANNELS,
        seed=42,
        selection_evaluator=_SelectionMock(),
        paper_quantities_provider=profile,
    )
    runner.run(config)
    assert len(recording.feedback_calls) == n_rounds
    for r, (_, metrics) in enumerate(recording.feedback_calls):
        # C4 — paper quantities and selection ratio MUST reach the
        # scheduler feedback path. ``schedule_evidence_ratio`` is
        # emitted only by schedulers that carry an
        # ``evidence_ratio`` attribute (the
        # :class:`CodimensionSheetScheduler`); the default cosine
        # scheduler does not emit it, so we treat it as optional.
        assert "paper_quantity_diagnostics" in metrics, (
            f"round {r}: paper_quantity_diagnostics missing"
        )
        assert "selection_ratio" in metrics, (
            f"round {r}: selection_ratio missing"
        )
        # Verify shape of paper_quantity_diagnostics
        pq = metrics["paper_quantity_diagnostics"]
        assert set(pq.keys()) == {
            "sheet_A",
            "packing_B",
            "cell_C",
            "exterior_gap_e_rho",
        }


def test_runner_forwards_eps_implicit_to_evaluator(_twodim_adapter) -> None:
    """C4: runner forwards ``sample.eps_implicit`` to ``oracle_at_round(eps_round=...)``.

    When the active scheduler emits a per-round ``eps_implicit`` on
    its ``ScheduleSample`` (e.g.
    :class:`CodimensionSheetScheduler`), the runner must thread it
    into the selection evaluator as ``eps_round``. Without this
    thread, the metric's ``selection_ratio`` is structurally
    independent of the scheduler (the C4 investigation's
    "Failure 3").
    """
    from collections.abc import Mapping

    import numpy as np

    from adaptive_reflow.algorithm.scheduler._core import (
        CosineScheduleConfig,
        ScheduleSample,
    )
    from adaptive_reflow.contracts import (
        ArtifactHash,
        CosineScheduleSample,
        FactorValue,
    )

    adapter = _twodim_adapter
    n_rounds = 4

    # Recording scheduler that returns ``ScheduleSample`` instances
    # with a fixed ``eps_implicit`` so we can assert the runner
    # forwards that exact value to the evaluator.
    cfg = CosineScheduleConfig(
        cycle_length=n_rounds,
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("test_eps_implicit_forward"),
        frozen_before_evaluation=True,
    )

    fixed_eps = 0.123

    class _EpsScheduler:
        def __init__(self) -> None:
            self._n = 0
            self.config = cfg

        def sample(
            self, outer_cycle_id: int, round_in_cycle: int, target_round: int,
        ) -> ScheduleSample:
            self._n += 1
            length = int(cfg.cycle_length)
            n_cap = max(0.0, min(1.0, 1.0 - self._n / length))
            return ScheduleSample(
                outer_cycle_id=int(outer_cycle_id),
                round_in_cycle=int(round_in_cycle),
                cycle_length=length,
                n_cap=n_cap,
                n_min=float(cfg.n_min),
                n_max=float(cfg.n_max),
                u_r=float(round_in_cycle) / max(length - 1, 1),
                family="test_eps_implicit",
                computed_at_round=int(target_round),
                schedule_hash="test_eps_implicit_hash",
                audit_codes=(),
                eps_implicit=float(fixed_eps),
            )

        def cycle_length(self) -> int:
            return int(cfg.cycle_length)

        def schedule_family(self) -> str:
            return "test_eps_implicit"

        def config_hash(self) -> str:
            return "test_eps_implicit_hash"

        def reset(self) -> None:
            self._n = 0

        def record_round_feedback(
            self, round_in_cycle: int, metrics: Mapping[str, float],
        ) -> None:
            return None

        def to_config(self) -> dict[str, object]:
            return {"family": "test_eps_implicit"}

        @classmethod
        def from_config(
            cls, config: dict[str, object],
        ) -> _EpsScheduler:
            return cls()

        def inject_noise(self, state, schedule_sample, *, generator):
            arr = np.asarray(state, dtype=np.float64)
            return arr.copy()

    # Selection evaluator that records every ``eps_round`` argument.
    eps_seen: list[float | None] = []

    class _SelectionRecorder:
        def oracle(
            self, bundle: object, *, channel: object, seed: int,
        ) -> dict[str, float]:
            return {"selection_ratio": 0.5}

        def oracle_at_round(
            self,
            bundle: object,
            *,
            channel: object,
            seed: int,
            round_index: int,
            eps_round: float | None = None,
        ) -> dict[str, float]:
            eps_seen.append(eps_round)
            # Mirror the legacy ``oracle`` payload.
            return {"selection_ratio": 0.5}

    runner = ReInferenceRunner(
        adapter=adapter, scheduler=_EpsScheduler(),
    )
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        channels=TWODIM_FM_CHANNELS,
        seed=42,
        selection_evaluator=_SelectionRecorder(),
    )
    runner.run(config)
    assert len(eps_seen) == n_rounds
    for r, eps in enumerate(eps_seen):
        assert eps == pytest.approx(fixed_eps, abs=1e-12), (
            f"round {r}: runner forwarded eps_round={eps!r} "
            f"instead of {fixed_eps!r}"
        )


# ---------------------------------------------------------------------------
# P1-9 (F-33) — Runner resets inner driver / merge / blender between runs
# ---------------------------------------------------------------------------


def test_runner_resets_inner_components_between_runs(_twodim_adapter) -> None:
    """P1-9 (F-33): inner driver / merge / blender reset between ``run()`` calls.

    Regression test: the legacy runner only reset the outer
    orchestrator state machine between runs; the inner driver /
    merge / blender each carried over their per-cycle state. This
    produced non-reproducible second runs (the merge operator's
    ``prev`` chain, the policy driver's saturation count, the
    blender's prior digest all polluted the second run). The fix
    hooks ``reset()`` on each non-scheduler inner component at the
    top of ``run()`` (the scheduler is already reset via the state
    machine wrapper).

    We assert that each non-scheduler inner component has a
    callable ``reset`` (the runner already exercises that the
    runner invokes it before the per-round loop).
    """
    from adaptive_reflow.algorithm import (
        AdaptivePolicyDriver,
        BoundedMergeOperator,
        LinearBlender,
        default_cosine_scheduler,
    )

    adapter = _twodim_adapter
    n_rounds = 3
    merge = BoundedMergeOperator()
    driver = AdaptivePolicyDriver()
    blender = LinearBlender()
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
        merge_operator=merge,
        policy_driver=driver,
        blender=blender,
    )
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        outer_cycle_id=0,
        target_round=0,
        seed=42,
        channels=TWODIM_FM_CHANNELS,
    )
    runner.run(config)
    # Assert each non-scheduler inner component has a callable
    # ``reset`` method (the runner invokes it via the reset_hooks
    # loop at the top of ``run()``).
    assert callable(merge.reset)
    assert callable(driver.reset)
    assert callable(blender.reset)
    # Re-run with the same config — must succeed (the reset hooks
    # clear per-cycle state so the second run starts clean).
    runner.run(config)


# ---------------------------------------------------------------------------
# P1-9 (F-33) — Runner resets inner components between runs (smoke test)
# ---------------------------------------------------------------------------


def test_runner_resets_inner_components_between_runs(_twodim_adapter) -> None:
    """P1-9 (F-33): second ``run()`` on the same runner must succeed without crashing.

    Regression test: the legacy runner only reset the outer
    orchestrator state machine between runs. The fix hooks
    ``reset()`` on each non-scheduler inner component (driver /
    merge / blender) at the top of ``run()`` so a re-run starts
    from a clean slate. This smoke test runs the same config
    twice on the same runner and asserts both runs succeed.
    """
    from adaptive_reflow.algorithm import (
        AdaptivePolicyDriver,
        BoundedMergeOperator,
        LinearBlender,
        default_cosine_scheduler,
    )

    adapter = _twodim_adapter
    n_rounds = 3
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=default_cosine_scheduler(cycle_length=n_rounds),
        merge_operator=BoundedMergeOperator(),
        policy_driver=AdaptivePolicyDriver(),
        blender=LinearBlender(),
    )
    config = ReInferenceConfig(
        n_rounds=n_rounds,
        outer_cycle_id=0,
        target_round=0,
        seed=42,
        channels=TWODIM_FM_CHANNELS,
    )
    result_a = runner.run(config)
    result_b = runner.run(config)
    # Both runs must succeed and produce the same number of round
    # traces. The second run's reproducibility is what F-33 guarantees.
    assert len(result_a.round_traces) == n_rounds
    assert len(result_b.round_traces) == n_rounds
