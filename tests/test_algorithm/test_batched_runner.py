"""Tests for :class:`BatchedTrajectoryRunner` and the underlying batched adapter surface.

The B5 architectural fix lives in two new pieces:

* :class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter.generate_trajectory`
  — vectorised RK4 over a ``(T, K, n_gen, 2)`` tensor; byte-deterministic
  under a fixed seed.
* :class:`adaptive_reflow.algorithm.batched_runner.BatchedTrajectoryRunner`
  — thin orchestrator that drives the batched surface per round and
  emits the W2 / selection-ratio histories.

Companion to ``docs/design/B5_BATCHED_TRAJECTORIES.md``. Phase-A additive
only: the legacy :class:`ReInferenceRunner` is untouched and the existing
1196-test baseline is preserved.
"""
from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
from adaptive_reflow.algorithm import (
    BatchedRunnerConfig,
    BatchedTrajectoryRunner,
    ConstantScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.batched_runner import (
    _w2_to_mode_centres,
)
from adaptive_reflow.eval.posterior_selection_evaluator import (
    EvidenceScaleGapMetric,
)

# ---------------------------------------------------------------------------
# Constants + fixtures
# ---------------------------------------------------------------------------


XY_CHANNEL = "xy"


@pytest.fixture(scope="module")
def _twodim_adapter(twodim_fm_weights_path) -> TwoDimFMAdapter:
    """Return a single ``TwoDimFMAdapter`` instance reused across tests."""
    return TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path, target="two_moons"
    )


def _make_config(
    *,
    adapter: TwoDimFMAdapter,
    cycle_length: int = 4,
    trajectories_per_round: int = 8,
    endpoints_per_trajectory: int = 16,
    scheduler=None,
    seed: int = 42,
    evaluator: EvidenceScaleGapMetric | None = None,
) -> BatchedRunnerConfig:
    """Build a deterministic :class:`BatchedRunnerConfig`."""
    if scheduler is None:
        scheduler = default_cosine_scheduler(cycle_length=cycle_length)
    return BatchedRunnerConfig(
        cycle_length=cycle_length,
        trajectories_per_round=trajectories_per_round,
        endpoints_per_trajectory=endpoints_per_trajectory,
        scheduler=scheduler,
        policy_driver=None,
        blender=None,
        selection_evaluator=evaluator,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Adapter surface — generate_trajectory / batched_integrate
# ---------------------------------------------------------------------------


class TestTwoDimFMAdapterBatchedSurface:
    """Verify the new batched RK4 / generate_trajectory surface."""

    def test_batched_integrate_returns_full_trajectory(self, _twodim_adapter) -> None:
        adapter = _twodim_adapter
        rng = np.random.default_rng(123)
        x0 = rng.standard_normal((4, 2))
        traj = adapter.batched_integrate(x0, t_steps=5, seed=0)
        assert traj.shape == (4, 6, 2)
        # Each batch row's ``t=0`` must equal its initial state.
        np.testing.assert_array_equal(traj[:, 0, :], x0)

    def test_batched_integrate_dormand_prince_raises(self) -> None:
        from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

        adapter = TwoDimFMAdapter(
            target="two_moons", integrator="dormand_prince"
        )
        with pytest.raises(NotImplementedError):
            adapter.batched_integrate(np.zeros((1, 2)), t_steps=5, seed=0)

    def test_generate_trajectory_shape(self, _twodim_adapter) -> None:
        adapter = _twodim_adapter
        out = adapter.generate_trajectory(
            n_trajectories=2,
            endpoints_per_trajectory=3,
            n_gen=4,
            seed=7,
        )
        assert out.shape == (2, 3, 4, 2)

    def test_generate_trajectory_byte_deterministic(self, _twodim_adapter) -> None:
        adapter = _twodim_adapter
        a = adapter.generate_trajectory(
            n_trajectories=4, endpoints_per_trajectory=3, n_gen=2, seed=99
        )
        b = adapter.generate_trajectory(
            n_trajectories=4, endpoints_per_trajectory=3, n_gen=2, seed=99
        )
        np.testing.assert_array_equal(a, b)

    def test_generate_trajectory_changes_with_seed(self, _twodim_adapter) -> None:
        adapter = _twodim_adapter
        a = adapter.generate_trajectory(
            n_trajectories=2, endpoints_per_trajectory=2, n_gen=2, seed=1
        )
        b = adapter.generate_trajectory(
            n_trajectories=2, endpoints_per_trajectory=2, n_gen=2, seed=2
        )
        assert not np.array_equal(a, b)


# ---------------------------------------------------------------------------
# BatchedTrajectoryRunner — happy path tests
# ---------------------------------------------------------------------------


class TestBatchedTrajectoryRunnerHappyPath:
    """Drive the runner end-to-end on a small canonical configuration."""

    def test_batched_runner_produces_endpoints_for_each_round(
        self, _twodim_adapter
    ) -> None:
        adapter = _twodim_adapter
        cfg = _make_config(
            adapter=adapter,
            cycle_length=3,
            trajectories_per_round=2,
            endpoints_per_trajectory=2,
        )
        result = BatchedTrajectoryRunner(cfg, adapter).run()
        assert len(result.per_round_endpoints) == 3
        # Each round contains exactly ``trajectories_per_round`` arrays
        # of shape ``(endpoints_per_trajectory, 2)``.
        for round_arr in result.per_round_endpoints:
            assert len(round_arr) == cfg.trajectories_per_round
            for traj_arr in round_arr:
                assert traj_arr.shape == (
                    cfg.endpoints_per_trajectory,
                    2,
                )

    def test_batched_runner_endpoints_have_correct_shape(
        self, _twodim_adapter
    ) -> None:
        adapter = _twodim_adapter
        cfg = _make_config(
            adapter=adapter,
            cycle_length=5,
            trajectories_per_round=4,
            endpoints_per_trajectory=8,
        )
        result = BatchedTrajectoryRunner(cfg, adapter).run()
        for round_arr in result.per_round_endpoints:
            assert len(round_arr) == 4
            for arr in round_arr:
                assert arr.shape == (8, 2)
                assert arr.dtype == np.float64

    def test_batched_runner_byte_deterministic_under_same_seed(
        self, _twodim_adapter
    ) -> None:
        adapter = _twodim_adapter
        cfg_a = _make_config(adapter=adapter, cycle_length=4, seed=2024)
        cfg_b = _make_config(adapter=adapter, cycle_length=4, seed=2024)
        runner_a = BatchedTrajectoryRunner(cfg_a, adapter)
        runner_b = BatchedTrajectoryRunner(cfg_b, adapter)
        result_a = runner_a.run()
        result_b = runner_b.run()
        assert result_a.per_round_w2 == pytest.approx(result_b.per_round_w2)
        assert result_a.per_round_n_cap == pytest.approx(result_b.per_round_n_cap)
        assert result_a.config_hash == result_b.config_hash
        # The endpoint coordinates are also bit-identical for the same seed.
        for r, (round_a, round_b) in enumerate(
            zip(
                result_a.per_round_endpoints,
                result_b.per_round_endpoints,
                strict=True,
            )
        ):
            assert len(round_a) == len(round_b)
            for t, (arr_a, arr_b) in enumerate(zip(round_a, round_b, strict=True)):
                np.testing.assert_array_equal(
                    arr_a,
                    arr_b,
                    err_msg=f"round {r} trajectory {t} mismatch",
                )

    def test_batched_runner_w2_decreases_over_rounds(self, _twodim_adapter) -> None:
        adapter = _twodim_adapter
        cfg = _make_config(
            adapter=adapter,
            cycle_length=10,
            trajectories_per_round=8,
            endpoints_per_trajectory=16,
            scheduler=default_cosine_scheduler(cycle_length=10),
        )
        result = BatchedTrajectoryRunner(cfg, adapter).run()
        first = result.per_round_w2[0]
        last = result.per_round_w2[-1]
        assert last < first, (
            f"expected final-round W2 ({last}) < first-round W2 ({first}); "
            f"trajectory = {result.per_round_w2!r}"
        )


# ---------------------------------------------------------------------------
# Selection-ratio behaviour
# ---------------------------------------------------------------------------


class TestBatchedTrajectoryRunnerSelectionRatio:
    """Exercise the selection_ratio path through EvidenceScaleGapMetric."""

    def test_batched_runner_selection_ratio_varies_with_scheduler(
        self, _twodim_adapter
    ) -> None:
        adapter = _twodim_adapter
        evaluator = EvidenceScaleGapMetric(target="two_moons", n_gen=64)
        cosine_cfg = _make_config(
            adapter=adapter,
            cycle_length=8,
            trajectories_per_round=8,
            endpoints_per_trajectory=8,
            scheduler=default_cosine_scheduler(cycle_length=8),
            evaluator=evaluator,
            seed=42,
        )
        constant_cfg = _make_config(
            adapter=adapter,
            cycle_length=8,
            trajectories_per_round=8,
            endpoints_per_trajectory=8,
            scheduler=ConstantScheduler(cycle_length=8, n_cap=1.0),
            evaluator=evaluator,
            seed=42,
        )
        cosine_result = BatchedTrajectoryRunner(cosine_cfg, adapter).run()
        constant_result = BatchedTrajectoryRunner(constant_cfg, adapter).run()
        assert cosine_result.per_round_selection_ratio is not None
        assert constant_result.per_round_selection_ratio is not None
        # Cosine + constant give different selection-ratio trajectories.
        assert (
            cosine_result.per_round_selection_ratio
            != constant_result.per_round_selection_ratio
        ), (
            f"selection_ratio identical across schedulers — "
            f"cosine = {cosine_result.per_round_selection_ratio!r}, "
            f"constant = {constant_result.per_round_selection_ratio!r}"
        )

    def test_batched_runner_selection_ratio_within_unit_interval(
        self, _twodim_adapter
    ) -> None:
        adapter = _twodim_adapter
        evaluator = EvidenceScaleGapMetric(target="two_moons", n_gen=64)
        cfg = _make_config(
            adapter=adapter,
            cycle_length=4,
            evaluator=evaluator,
            seed=7,
        )
        result = BatchedTrajectoryRunner(cfg, adapter).run()
        assert result.per_round_selection_ratio is not None
        for ratio in result.per_round_selection_ratio:
            assert 0.0 <= ratio <= 1.0, (
                f"selection_ratio must lie in [0, 1]; got {ratio!r}"
            )

    def test_batched_runner_selection_ratio_none_when_no_evaluator(
        self, _twodim_adapter
    ) -> None:
        adapter = _twodim_adapter
        cfg = _make_config(adapter=adapter, evaluator=None)
        result = BatchedTrajectoryRunner(cfg, adapter).run()
        assert result.per_round_selection_ratio is None


# ---------------------------------------------------------------------------
# EvidenceScaleGapMetric — evaluate_trajectory surface
# ---------------------------------------------------------------------------


class TestEvidenceScaleGapMetricTrajectory:
    """Verify the new batched metric entry point."""

    def test_evaluate_trajectory_accepts_k_n_gen_2(self) -> None:
        evaluator = EvidenceScaleGapMetric(target="two_moons")
        rng = np.random.default_rng(0)
        endpoints = rng.standard_normal((4, 8, 2))  # K=4, n_gen=8, dim=2
        from adaptive_reflow.contracts import ChannelName

        ev = evaluator.evaluate_trajectory(
            endpoints, channel=ChannelName("xy"), seed=42
        )
        assert 0.0 <= ev.bounded_score <= 1.0
        # Regression guard: the legacy ``evaluate`` / ``oracle`` pair
        # is still callable (backward-compat per Phase-A additive).
        assert callable(evaluator.evaluate)
        assert callable(evaluator.oracle)

    def test_evaluate_trajectory_accepts_2d_population(self) -> None:
        evaluator = EvidenceScaleGapMetric(target="two_moons")
        rng = np.random.default_rng(0)
        endpoints = rng.standard_normal((32, 2))
        from adaptive_reflow.contracts import ChannelName

        ev = evaluator.evaluate_trajectory(
            endpoints, channel=ChannelName("xy"), seed=0
        )
        assert 0.0 <= ev.bounded_score <= 1.0

    def test_oracle_batched_matches_evaluate_trajectory(self) -> None:
        evaluator = EvidenceScaleGapMetric(target="two_moons")
        rng = np.random.default_rng(123)
        endpoints = rng.standard_normal((4, 4, 2))
        from adaptive_reflow.contracts import ChannelName

        ev = evaluator.evaluate_trajectory(
            endpoints, channel=ChannelName("xy"), seed=99
        )
        oracle = evaluator.oracle_batched(
            endpoints, channel=ChannelName("xy"), seed=99
        )
        assert oracle["selection_ratio"] == pytest.approx(ev.raw_score)
        assert oracle["bounded_score"] == pytest.approx(ev.bounded_score)


# ---------------------------------------------------------------------------
# Internal helpers — regression coverage
# ---------------------------------------------------------------------------


class TestBatchedRunnerInternalHelpers:
    """Pure-function coverage for the W2 helper."""

    def test_w2_to_mode_centres_constant_endpoint_returns_zero(self) -> None:
        centres = np.array([[0.0, 0.0], [1.0, 1.0]])
        # An endpoint exactly on a centre yields zero W2.
        pts = np.array([[0.0, 0.0]])
        assert _w2_to_mode_centres(pts, centres) == 0.0

    def test_w2_to_mode_centres_grows_with_distance(self) -> None:
        centres = np.array([[0.0, 0.0]])
        near = np.array([[0.1, 0.0]])
        far = np.array([[1.0, 0.0]])
        assert _w2_to_mode_centres(far, centres) > _w2_to_mode_centres(
            near, centres
        )

    def test_w2_to_mode_centres_empty_input_returns_zero(self) -> None:
        centres = np.array([[0.0, 0.0]])
        assert _w2_to_mode_centres(np.zeros((0, 2)), centres) == 0.0
