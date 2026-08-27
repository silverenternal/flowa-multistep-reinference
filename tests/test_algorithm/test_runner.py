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
    ConstantPolicyDriver,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
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
    its :meth:`compute_policy` method. Both must produce the same
    ``applied_policy_hash`` and ``endpoint_digest`` for every round.
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
        # The endpoint digest must match (the policy is identical so
        # the round produces the same endpoint trajectory).
        assert str(legacy_trace.endpoint_digest) == str(
            runner_trace.endpoint_digest
        ), (
            f"round {r}: endpoint_digest mismatch; "
            f"legacy={legacy_trace.endpoint_digest!r} "
            f"runner={runner_trace.endpoint_digest!r}"
        )
        # The initial state digest must match.
        assert str(legacy_trace.initial_state_digest) == str(
            runner_trace.initial_state_digest
        )
        # The integrator trace (ODE output) must match.
        assert (
            legacy_trace.integrator_trace is not None
            and runner_trace.integrator_trace is not None
        )
        assert (
            str(legacy_trace.integrator_trace.native_state_digest)
            == str(runner_trace.integrator_trace.native_state_digest)
        )
        # The condition_digest must match.
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
        # equal n_cap for every round.
        assert metrics["beta"] == pytest.approx(metrics["n_cap"])


# ---------------------------------------------------------------------------
# 2. Mixed scheduler + driver (impossible in the old code)
# ---------------------------------------------------------------------------


def test_runner_with_constant_scheduler_and_cosine_driver(_twodim_adapter) -> None:
    """A *mixed* configuration the old code couldn't express.

    Scheduler: ``CosineAnnealScheduler`` (varying ``n_cap`` across
    rounds). Driver: ``ConstantPolicyDriver(beta=0.5)`` (ignores the
    schedule). Result: ``beta`` is constant at 0.5 every round even
    though the schedule's ``n_cap`` is varying. This configuration is
    impossible in the old code (the engine either applied
    ``beta = n_cap`` via the inline override or used the caller's
    explicit ``beta``; the cross-product was unreachable). The new
    framework composes ``(scheduler, driver)`` freely so the test
    verifies the runner produces a well-defined result.
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
    # Per-round metrics: beta is constant at 0.5, n_cap follows the cosine ramp.
    betas = [result.per_round_metrics[r]["beta"] for r in range(n_rounds)]
    n_caps = [result.per_round_metrics[r]["n_cap"] for r in range(n_rounds)]
    assert betas == pytest.approx([0.5, 0.5, 0.5, 0.5]), (
        f"mixed config: beta should be constant at 0.5; got {betas!r}"
    )
    # The schedule's n_cap is varying (cosine annealing) so the
    # constant driver truly is overriding the schedule.
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
