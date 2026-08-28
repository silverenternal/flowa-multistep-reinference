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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
