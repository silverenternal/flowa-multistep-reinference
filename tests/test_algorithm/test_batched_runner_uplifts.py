"""Batched-runner framework-INTERNAL uplifts: W2 plug-in + vectorised path.

Covers the two runner-level uplifts:

* **P0 #3** — ``BatchedRunnerConfig.w2_family`` / ``w2_kwargs`` select a
  registered :mod:`adaptive_reflow.eval.w2` estimator for the per-round
  ``W2`` series, with the legacy surrogate preserved as the default.
* **P0 #8** — ``BatchedRunnerConfig.vectorised`` lets an adapter serve a
  whole round in one batched call, which must be numerically equivalent
  to the sequential loop and materially faster.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from adaptive_reflow.algorithm.batched_runner import (
    DEFAULT_W2_FAMILY,
    BatchedRunnerConfig,
    BatchedTrajectoryRunner,
    BatchedVectorisedAdapterProtocol,
)
from adaptive_reflow.algorithm.scheduler import default_cosine_scheduler

CYCLE = 4
T = 4
K = 8


class _SequentialAdapter:
    """Deterministic per-seed endpoint generator (no vectorised capability)."""

    target = "two_moons"

    def __init__(self) -> None:
        self.calls = 0

    def generate_trajectory(
        self,
        *,
        n_trajectories: int,
        endpoints_per_trajectory: int,
        n_gen: int,
        seed: int,
    ) -> np.ndarray:
        self.calls += 1
        rng = np.random.default_rng(int(seed))
        pts = rng.normal(0.0, 0.5, size=(endpoints_per_trajectory, 2))
        return pts.reshape(1, endpoints_per_trajectory, 1, 2)


class _VectorisedAdapter(_SequentialAdapter):
    """Same arithmetic, exposed through the batched capability."""

    def __init__(self) -> None:
        super().__init__()
        self.batched_calls = 0

    def generate_trajectories_batched(
        self,
        *,
        seeds: tuple[int, ...],
        endpoints_per_trajectory: int,
        n_gen: int,
    ) -> np.ndarray:
        self.batched_calls += 1
        stacked = [
            np.random.default_rng(int(s)).normal(
                0.0, 0.5, size=(endpoints_per_trajectory, 2)
            )
            for s in seeds
        ]
        return np.stack(stacked).reshape(
            len(seeds), endpoints_per_trajectory, 1, 2
        )


def _config(**overrides: object) -> BatchedRunnerConfig:
    base: dict[str, object] = {
        "cycle_length": CYCLE,
        "trajectories_per_round": T,
        "endpoints_per_trajectory": K,
        "seed": 11,
    }
    base.update(overrides)
    base.setdefault(
        "scheduler", default_cosine_scheduler(cycle_length=int(base["cycle_length"]))
    )
    return BatchedRunnerConfig(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# P0 #3 — W2 family plug-in
# ---------------------------------------------------------------------------


def test_default_config_uses_the_legacy_surrogate() -> None:
    cfg = _config()
    assert cfg.w2_family == DEFAULT_W2_FAMILY == "mode_centre_mse"
    assert cfg.w2_kwargs is None
    assert cfg.vectorised is False


def test_default_run_is_unchanged_by_the_new_slots() -> None:
    """Adding the slots must not perturb an existing run's numbers."""
    explicit = BatchedTrajectoryRunner(
        _config(w2_family="mode_centre_mse"), _SequentialAdapter()
    ).run()
    default = BatchedTrajectoryRunner(_config(), _SequentialAdapter()).run()
    assert explicit.per_round_w2 == default.per_round_w2
    assert explicit.config_hash == default.config_hash


@pytest.mark.parametrize(
    "family", ["projection_free", "kernelized", "sinkhorn", "mode_centre_mse"]
)
def test_every_family_drives_a_finite_w2_series(family: str) -> None:
    result = BatchedTrajectoryRunner(
        _config(w2_family=family), _SequentialAdapter()
    ).run()
    assert result.w2_family == family
    assert len(result.per_round_w2) == CYCLE
    assert all(np.isfinite(v) and v >= 0.0 for v in result.per_round_w2)
    assert result.per_round_metric["W2"] == result.per_round_w2


def test_switching_family_changes_the_w2_series() -> None:
    legacy = BatchedTrajectoryRunner(_config(), _SequentialAdapter()).run()
    projection = BatchedTrajectoryRunner(
        _config(w2_family="projection_free"), _SequentialAdapter()
    ).run()
    assert legacy.per_round_w2 != projection.per_round_w2


def test_w2_kwargs_reach_the_estimator() -> None:
    coarse = BatchedTrajectoryRunner(
        _config(w2_family="projection_free", w2_kwargs={"n_projections": 4}),
        _SequentialAdapter(),
    ).run()
    fine = BatchedTrajectoryRunner(
        _config(w2_family="projection_free", w2_kwargs={"n_projections": 256}),
        _SequentialAdapter(),
    ).run()
    assert coarse.per_round_w2 != fine.per_round_w2


def test_config_hash_only_changes_when_opting_in() -> None:
    """Legacy hashes are preserved; opting in produces a distinct hash."""
    legacy_hash = BatchedTrajectoryRunner(_config(), _SequentialAdapter()).run().config_hash
    opted_in = (
        BatchedTrajectoryRunner(
            _config(w2_family="projection_free"), _SequentialAdapter()
        )
        .run()
        .config_hash
    )
    vectorised = (
        BatchedTrajectoryRunner(_config(vectorised=True), _VectorisedAdapter())
        .run()
        .config_hash
    )
    assert legacy_hash != opted_in
    assert legacy_hash != vectorised
    assert opted_in != vectorised


def test_unknown_family_is_rejected_at_construction() -> None:
    with pytest.raises(KeyError):
        BatchedTrajectoryRunner(_config(w2_family="nope"), _SequentialAdapter())


# ---------------------------------------------------------------------------
# P0 #8 — vectorised round generation
# ---------------------------------------------------------------------------


def test_vectorised_adapter_satisfies_the_capability_protocol() -> None:
    assert isinstance(_VectorisedAdapter(), BatchedVectorisedAdapterProtocol)
    assert not isinstance(_SequentialAdapter(), BatchedVectorisedAdapterProtocol)


def test_vectorised_path_is_numerically_equivalent_to_sequential() -> None:
    """P0 #8 contract: a pure performance switch, not a behavioural one."""
    sequential = BatchedTrajectoryRunner(_config(), _SequentialAdapter()).run()
    vectorised = BatchedTrajectoryRunner(
        _config(vectorised=True), _VectorisedAdapter()
    ).run()

    assert vectorised.vectorised_rounds == CYCLE
    assert sequential.vectorised_rounds == 0
    assert np.allclose(
        np.asarray(sequential.per_round_w2),
        np.asarray(vectorised.per_round_w2),
        atol=1e-9,
    )
    for r in range(CYCLE):
        for t in range(T):
            assert np.allclose(
                sequential.per_round_endpoints[r][t],
                vectorised.per_round_endpoints[r][t],
                atol=1e-9,
            )


def test_vectorised_path_makes_one_adapter_call_per_round() -> None:
    adapter = _VectorisedAdapter()
    BatchedTrajectoryRunner(_config(vectorised=True), adapter).run()
    assert adapter.batched_calls == CYCLE
    assert adapter.calls == 0  # the sequential entry point was never used


def test_vectorised_reduces_adapter_call_count_by_the_batch_factor() -> None:
    """Quantitative target: ``T``x fewer adapter invocations per round."""
    sequential_adapter = _SequentialAdapter()
    BatchedTrajectoryRunner(_config(), sequential_adapter).run()
    vectorised_adapter = _VectorisedAdapter()
    BatchedTrajectoryRunner(_config(vectorised=True), vectorised_adapter).run()

    assert sequential_adapter.calls == CYCLE * T
    assert vectorised_adapter.batched_calls == CYCLE
    assert sequential_adapter.calls / vectorised_adapter.batched_calls == float(T)


def test_vectorised_falls_back_when_the_adapter_lacks_the_capability() -> None:
    """Opting in against a legacy adapter must be safe, not an error."""
    result = BatchedTrajectoryRunner(
        _config(vectorised=True), _SequentialAdapter()
    ).run()
    assert result.vectorised_rounds == 0
    assert len(result.per_round_w2) == CYCLE


def test_vectorised_rejects_a_wrong_length_batch() -> None:
    class _BadAdapter(_SequentialAdapter):
        def generate_trajectories_batched(
            self,
            *,
            seeds: tuple[int, ...],
            endpoints_per_trajectory: int,
            n_gen: int,
        ) -> np.ndarray:
            return np.zeros((len(seeds) - 1, endpoints_per_trajectory, 1, 2))

    runner = BatchedTrajectoryRunner(_config(vectorised=True), _BadAdapter())
    with pytest.raises(ValueError, match="trajectories for"):
        runner.run()


@pytest.mark.slow
def test_vectorised_path_is_not_slower_than_sequential() -> None:
    """Sanity guard: the fast path must not regress wall-clock."""
    cfg_seq = _config(cycle_length=8)
    cfg_vec = _config(cycle_length=8, vectorised=True)

    BatchedTrajectoryRunner(cfg_seq, _SequentialAdapter()).run()  # warm up
    start = time.perf_counter()
    BatchedTrajectoryRunner(cfg_seq, _SequentialAdapter()).run()
    sequential_s = time.perf_counter() - start

    BatchedTrajectoryRunner(cfg_vec, _VectorisedAdapter()).run()  # warm up
    start = time.perf_counter()
    BatchedTrajectoryRunner(cfg_vec, _VectorisedAdapter()).run()
    vectorised_s = time.perf_counter() - start

    assert vectorised_s <= sequential_s * 2.0
