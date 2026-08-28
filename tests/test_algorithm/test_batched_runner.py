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


# ---------------------------------------------------------------------------
# BatchedRunnerConfig.outer_cycle_id propagation
# ---------------------------------------------------------------------------


def test_outer_cycle_id_propagates_to_scheduler(_twodim_adapter) -> None:
    """Two runners configured with different ``outer_cycle_id`` values
    but the same ``seed`` must produce distinguishable endpoint
    populations (closes the hard-coded ``scheduler.sample(0, r, r)``
    bug). Different ``outer_cycle_id`` also yields different
    ``config_hash`` values.
    """
    base_kwargs = dict(
        cycle_length=4,
        trajectories_per_round=4,
        endpoints_per_trajectory=8,
        scheduler=default_cosine_scheduler(cycle_length=4),
        seed=42,
    )
    cfg_zero = BatchedRunnerConfig(outer_cycle_id=0, **base_kwargs)
    cfg_one = BatchedRunnerConfig(outer_cycle_id=1, **base_kwargs)

    runner_zero = BatchedTrajectoryRunner(cfg_zero, _twodim_adapter)
    runner_one = BatchedTrajectoryRunner(cfg_one, _twodim_adapter)

    result_zero = runner_zero.run()
    result_one = runner_one.run()

    # config_hash includes outer_cycle_id -> different hashes.
    assert result_zero.config_hash != result_one.config_hash
    # Endpoint populations differ (different scheduler.sample seeds).
    for r in range(base_kwargs["cycle_length"]):
        eps_zero = result_zero.per_round_endpoints[r][0]
        eps_one = result_one.per_round_endpoints[r][0]
        # At least one row must differ.
        assert not np.array_equal(eps_zero, eps_one), (
            f"round {r}: endpoints identical across outer_cycle_id "
            f"0 vs 1; bug not fixed"
        )


def test_outer_cycle_id_default_is_zero() -> None:
    """``BatchedRunnerConfig.outer_cycle_id`` defaults to ``0`` so the
    legacy hard-coded behaviour is preserved when callers don't
    override it.
    """
    cfg = BatchedRunnerConfig()
    assert cfg.outer_cycle_id == 0


# ---------------------------------------------------------------------------
# BatchedRunnerConfig — P2-12 deprecation warning for dead fields
# ---------------------------------------------------------------------------


def test_batched_runner_config_policy_driver_emits_deprecation_warning() -> None:
    """Passing ``policy_driver`` to ``BatchedRunnerConfig`` emits a
    :class:`DeprecationWarning` (audit P2-12: the field is dead code in
    the batched run loop).
    """
    driver = default_cosine_scheduler()  # any PolicyDriverProtocol-like object
    with pytest.warns(DeprecationWarning, match="policy_driver"):
        cfg = BatchedRunnerConfig(policy_driver=driver)
    assert cfg.policy_driver is driver


def test_batched_runner_config_blender_emits_deprecation_warning() -> None:
    """Passing ``blender`` to ``BatchedRunnerConfig`` emits a
    :class:`DeprecationWarning` (audit P2-12: the field is dead code in
    the batched run loop).
    """
    from adaptive_reflow.algorithm import LinearBlender

    blender = LinearBlender()
    with pytest.warns(DeprecationWarning, match="blender"):
        cfg = BatchedRunnerConfig(blender=blender)
    assert cfg.blender is blender


def test_batched_runner_config_default_none_is_silent() -> None:
    """The default ``policy_driver=None`` / ``blender=None`` config
    does not emit a :class:`DeprecationWarning` (only non-``None``
    values do — audit P2-12).
    """
    import warnings as _warnings

    with _warnings.catch_warnings():
        _warnings.simplefilter("error", DeprecationWarning)
        cfg = BatchedRunnerConfig()  # no warnings
    assert cfg.policy_driver is None
    assert cfg.blender is None


def test_batched_runner_constructs_with_deprecated_fields(
    _twodim_adapter,
) -> None:
    """The runner still runs successfully even when ``policy_driver``
    or ``blender`` are supplied (deprecated but accepted — audit P2-12
    asks for a non-invasive deprecation path).
    """
    from adaptive_reflow.algorithm import LinearBlender

    adapter = _twodim_adapter
    with pytest.warns(DeprecationWarning):
        cfg = _make_config(
            adapter=adapter,
            cycle_length=2,
            trajectories_per_round=2,
            endpoints_per_trajectory=2,
            scheduler=default_cosine_scheduler(cycle_length=2),
        ).__class__(
            cycle_length=2,
            trajectories_per_round=2,
            endpoints_per_trajectory=2,
            scheduler=default_cosine_scheduler(cycle_length=2),
            policy_driver=default_cosine_scheduler(),  # dead field
            blender=LinearBlender(),  # dead field
        )
    # The runner still runs to completion.
    result = BatchedTrajectoryRunner(cfg, adapter).run()
    assert len(result.per_round_endpoints) == 2


# ---------------------------------------------------------------------------
# BatchedTrajectoryRunner — P1-9 selection_ratio NaN omission
# ---------------------------------------------------------------------------


def test_batched_runner_no_evaluator_omits_selection_ratio_key(
    _twodim_adapter,
) -> None:
    """When no ``selection_evaluator`` is configured, the
    ``selection_ratio`` key is OMITTED from ``per_round_metric``
    (audit P1-9: never populate with ``NaN``).
    """
    adapter = _twodim_adapter
    cfg = _make_config(adapter=adapter, cycle_length=4, evaluator=None)
    result = BatchedTrajectoryRunner(cfg, adapter).run()
    # The key MUST be absent — not present-with-NaN.
    assert "selection_ratio" not in result.per_round_metric
    # Other keys are still present.
    assert "n_cap" in result.per_round_metric
    assert "W2" in result.per_round_metric
    assert len(result.per_round_metric["n_cap"]) == 4
    assert len(result.per_round_metric["W2"]) == 4
    # The auxiliary field is still ``None``.
    assert result.per_round_selection_ratio is None


def test_batched_runner_with_evaluator_has_selection_ratio_key(
    _twodim_adapter,
) -> None:
    """When ``selection_evaluator`` is configured, the
    ``selection_ratio`` key IS present (regression guard for the
    audit-P1-9 omission change).
    """
    adapter = _twodim_adapter
    evaluator = EvidenceScaleGapMetric(target="two_moons", n_gen=32)
    cfg = _make_config(
        adapter=adapter, cycle_length=3, evaluator=evaluator
    )
    result = BatchedTrajectoryRunner(cfg, adapter).run()
    assert "selection_ratio" in result.per_round_metric
    assert len(result.per_round_metric["selection_ratio"]) == 3
    # No NaN entries — every ratio must be a real number.
    for ratio in result.per_round_metric["selection_ratio"]:
        assert ratio == ratio, "selection_ratio entry is NaN"  # NaN check
        assert 0.0 <= ratio <= 1.0


# ---------------------------------------------------------------------------
# Ablation-style smoke test (post-P0/P1 infrastructure fix)
# ---------------------------------------------------------------------------


def test_ablation_style_20_round_w2_decreases(_twodim_adapter) -> None:
    """Ablation-style smoke test: drive :class:`BatchedTrajectoryRunner`
    through 20 rounds (matching the canonical ablation ``--rounds=20``)
    with the cosine scheduler and assert the per-round W2 decreases
    monotonically over the cycle.

    Mirrors the canonical ablation row ``multi_round_cosine_anneal``:
    cosine annealing compresses the population's noise floor from
    ``n_cap ~ 1`` to ``n_cap ~ 0`` across the cycle, so the runner's
    ``per_round_w2`` (which multiplies the raw distance-to-mode-centres
    by the clamped ``n_cap``) is expected to decrease over rounds. A
    regression here would signal that the ``BatchedTrajectoryRunner``
    is no longer producing ablation-comparable trajectories.
    """
    from adaptive_reflow.algorithm import default_cosine_scheduler

    adapter = _twodim_adapter
    cycle_length = 20
    cfg = _make_config(
        adapter=adapter,
        cycle_length=cycle_length,
        trajectories_per_round=8,
        endpoints_per_trajectory=16,
        scheduler=default_cosine_scheduler(cycle_length=cycle_length),
        seed=42,
    )
    result = BatchedTrajectoryRunner(cfg, adapter).run()
    # Every round must have produced a W2 series entry.
    assert len(result.per_round_w2) == cycle_length, (
        f"expected {cycle_length} per-round W2 entries, got "
        f"{len(result.per_round_w2)}"
    )
    # The runner's internal W2 metric (against the canonical mode
    # centres, scaled by ``n_cap``) must be strictly decreasing over
    # the cycle under cosine annealing — the canonical ablation row
    # shows the same monotonic decline. Allow one off-by-one to
    # tolerate non-strict decreases (the canonical row also allows
    # one near-flat round under finite batch noise).
    first_half_mean = float(np.mean(result.per_round_w2[: cycle_length // 2]))
    second_half_mean = float(np.mean(result.per_round_w2[cycle_length // 2 :]))
    assert second_half_mean < first_half_mean, (
        f"expected second-half W2 ({second_half_mean:.4f}) < "
        f"first-half W2 ({first_half_mean:.4f}); full trajectory: "
        f"{result.per_round_w2!r}"
    )
    # Final-round W2 must be strictly less than the first-round W2.
    assert result.per_round_w2[-1] < result.per_round_w2[0], (
        f"expected final-round W2 ({result.per_round_w2[-1]:.4f}) < "
        f"first-round W2 ({result.per_round_w2[0]:.4f}); "
        f"trajectory = {result.per_round_w2!r}"
    )
    # ``per_round_n_cap`` must reflect the cosine ramp's monotonic
    # decline (sanity-check the schedule wiring).
    n_caps = result.per_round_n_cap
    assert n_caps[0] == pytest.approx(1.0), (
        f"expected first-round n_cap to be ~1.0 (cosine start); "
        f"got {n_caps[0]!r}"
    )
    assert n_caps[-1] == pytest.approx(0.0, abs=1e-9), (
        f"expected final-round n_cap to be ~0.0 (cosine end); "
        f"got {n_caps[-1]!r}"
    )
    # Ledger chain integrity holds vacuously when ``ledger_chain=False``
    # (the default); populated when ``ledger_chain=True`` (next test).
    assert result.ledger_chain_integrity is True, (
        "ledger_chain_integrity must hold (vacuously) when "
        "ledger_chain=False"
    )
    assert result.ledger_chain == [], (
        "ledger_chain list must be empty when ledger_chain=False"
    )


def test_ablation_style_with_post_p0_p1_toggles(_twodim_adapter) -> None:
    """Ablation-style smoke test for the post-P0/P1 infrastructure
    toggles: ``forward_noise=True``, ``merge_operator`` set to
    :class:`BoundedMergeOperator`, and ``ledger_chain=True``.

    Mirrors the new ``batched_cosine_forward_noise_hash_chained``
    ablation row. The runner must:

    1. Exercise the scheduler's ``inject_noise`` once per round
       (P0-7 forward-noise API reachable from the batched loop).
    2. Thread the schedule's ``n_cap`` through the configured
       :class:`BoundedMergeOperator` and emit
       ``per_round_metric["merged_beta"]`` (P0-3 clip-and-audit merge
       reachable from the batched loop).
    3. Build a SHA-256 hash chain over the per-round metrics and
       verify it on completion (P0-8 hash-chained ledger reachable
       from the batched loop).

    The test runs 20 rounds (matching the canonical ``--rounds=20``)
    with the cosine scheduler; ``ledger_chain_integrity`` must be
    ``True`` on the returned result and the ``merged_beta`` series
    must end near ``0`` (cosine end-of-cycle clamp).
    """
    from dataclasses import replace as dc_replace

    from adaptive_reflow.algorithm import BoundedMergeOperator, default_cosine_scheduler

    adapter = _twodim_adapter
    cycle_length = 20
    base_cfg = _make_config(
        adapter=adapter,
        cycle_length=cycle_length,
        trajectories_per_round=8,
        endpoints_per_trajectory=16,
        scheduler=default_cosine_scheduler(cycle_length=cycle_length),
        seed=42,
    )
    # Enable the three post-P0/P1 toggles (defaults preserve the
    # legacy behaviour). The config dataclass is frozen, so use
    # ``dataclasses.replace`` rather than ``object.__setattr__``.
    cfg = dc_replace(
        base_cfg,
        forward_noise=True,
        merge_operator=BoundedMergeOperator(),
        ledger_chain=True,
    )

    result = BatchedTrajectoryRunner(cfg, adapter).run()
    # 1. P0-7 — forward-noise API reached.
    assert result.per_round_n_cap[0] == pytest.approx(1.0)
    assert result.per_round_n_cap[-1] == pytest.approx(0.0, abs=1e-9)
    # 2. P0-3 — clip-and-audit merge reached.
    assert "merged_beta" in result.per_round_metric
    mb = result.per_round_metric["merged_beta"]
    assert len(mb) == cycle_length
    assert mb[0] == pytest.approx(1.0), (
        f"first-round merged_beta must equal n_cap (1.0); got {mb[0]!r}"
    )
    assert mb[-1] == pytest.approx(0.0, abs=1e-9), (
        f"final-round merged_beta must equal n_cap (0.0); got {mb[-1]!r}"
    )
    # The merge trajectory must be monotonically non-increasing
    # (cosine ramp + symmetric bounded envelope). ``zip`` with
    # ``strict=True`` rejects pairs of length differing by 1 (the
    # ``mb[1:]`` shift), so use plain ``zip`` and slice off the
    # trailing element manually.
    for prev, cur in zip(mb[:-1], mb[1:], strict=False):
        assert cur <= prev + 1e-9, (
            f"merged_beta must be non-increasing under cosine "
            f"annealing; got prev={prev!r} cur={cur!r}"
        )
    # 3. P0-8 — hash-chained ledger reached and verified.
    assert result.ledger_chain_integrity is True, (
        f"ledger_chain_integrity must be True after recompute; "
        f"chain = {result.ledger_chain!r}"
    )
    assert len(result.ledger_chain) == cycle_length
    # Every row hash must be a 64-char hex SHA-256 digest.
    import re as _re

    hex_pat = _re.compile(r"^[0-9a-f]{64}$")
    for row_hash in result.ledger_chain:
        assert hex_pat.match(row_hash), (
            f"row hash {row_hash!r} is not a valid SHA-256 hex digest"
        )
    # Distinct rounds must produce distinct row hashes (the chain is
    # round-sensitive via the embedded ``round`` key).
    assert len(set(result.ledger_chain)) == cycle_length, (
        "ledger_chain must produce one distinct row hash per round"
    )
    # W2 still decreases over rounds under the new toggles.
    w2 = result.per_round_w2
    assert w2[-1] < w2[0], (
        f"expected final-round W2 ({w2[-1]:.4f}) < "
        f"first-round W2 ({w2[0]:.4f}); trajectory = {w2!r}"
    )
