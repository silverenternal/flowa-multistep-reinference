"""GAP-80 — two defects in the multi-round path that R5a is scored on.

Both tests pin *observed* behaviour with file-level evidence; they are
characterisation tests, not endorsements. When the fixes land they must be
inverted together with ``docs/audit/gap80-r5a-harness.md``.

F1 — ``BatchedTrajectoryRunner`` (the path behind
``tools/run_sota_2d_experiment._drive_batched``) never calls
``apply_restart_distribution``. ``generate_trajectory`` draws a fresh
``x0 ~ N(0, I_2)`` every round, so round ``r+1`` is an independent sample of
the same generator and the "multi-round framework" arm is the baseline sampled
``cycle_length`` times with different seeds.

F2 — ``TwoDimFMAdapter.apply_restart_distribution`` derives its fresh draw from
``(policy.policy_hash, next_round)`` only. The policy hash does not depend on
the record, so at ``m = 0`` every record restarts from the *same* point: the
blend ``m * prior_i + (1 - m) * fresh_common`` contracts the population's
variance by ``m^2`` and adds a common offset.
"""

from __future__ import annotations

import numpy as np

from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
from adaptive_reflow.algorithm.runner.batched_runner import (
    BatchedRunnerConfig,
    BatchedTrajectoryRunner,
)
from tools.eval.framework import _make_framework_policy
from tools.run_sota_2d_experiment import _build_cosine_scheduler


class _CountingAdapter(TwoDimFMAdapter):
    """TwoDimFMAdapter that records every restart-policy dispatch."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.restart_calls: list[int] = []

    def apply_restart_distribution(self, state, policy):  # type: ignore[no-untyped-def]
        self.restart_calls.append(int(state.source_round))
        return super().apply_restart_distribution(state, policy)


def test_f1_batched_path_never_dispatches_the_restart() -> None:
    """Three rounds, zero restart calls — the R5a path as shipped."""
    adapter = _CountingAdapter(target="two_moons")
    cfg = BatchedRunnerConfig(
        cycle_length=3,
        trajectories_per_round=2,
        endpoints_per_trajectory=2,
        scheduler=_build_cosine_scheduler(3),
        seed=7,
        selection_evaluator=None,
    )
    result = BatchedTrajectoryRunner(cfg, adapter).run()
    assert len(result.per_round_endpoints) == 3
    assert adapter.restart_calls == []
    # n_cap does vary, so the schedule is live — only the restart is absent.
    assert [round(float(x), 3) for x in result.per_round_n_cap] == [1.0, 0.5, 0.0]


def test_f2_fresh_restart_draw_is_record_invariant() -> None:
    """At ``m = 0`` the blend *is* the fresh draw; it must not be shared."""
    adapter = TwoDimFMAdapter(target="two_moons")
    # beta = 1 -> memory fraction m = 0 -> blended_x0 == fresh_x0.
    policy = _make_framework_policy(
        adapter, target_round=1, seed=42, beta_override=1.0
    )
    drawn = []
    for i in range(3):
        bundle = adapter.build_initial_state(batch_id="gap80", sample_id=f"rec{i}")
        restarted = adapter.apply_restart_distribution(bundle, policy)
        entry = adapter._native_states[restarted.native_state_digest]  # noqa: SLF001
        drawn.append(np.asarray(entry["x0"], dtype=np.float64).copy())
    # Defect: all three records share one fresh point.
    assert np.array_equal(drawn[0], drawn[1])
    assert np.array_equal(drawn[0], drawn[2])


def test_f2_shared_draw_contracts_the_population() -> None:
    """The population's spread after the blend is ``m`` x the prior's."""
    adapter = TwoDimFMAdapter(target="two_moons")
    m = 0.5
    policy = _make_framework_policy(
        adapter, target_round=1, seed=42, beta_override=1.0 - m
    )
    xs = []
    for i in range(200):
        bundle = adapter.build_initial_state(
            batch_id="gap80", sample_id=f"rec{i}"
        )
        prior = adapter._native_states[bundle.native_state_digest]  # noqa: SLF001
        restarted = adapter.apply_restart_distribution(bundle, policy)
        entry = adapter._native_states[restarted.native_state_digest]  # noqa: SLF001
        xs.append(
            (
                np.asarray(prior["x0"], dtype=np.float64),
                np.asarray(entry["x0"], dtype=np.float64),
            )
        )
    prior_sd = float(np.std(np.stack([p for p, _ in xs])[:, 0], ddof=1))
    blended_sd = float(np.std(np.stack([b for _, b in xs])[:, 0], ddof=1))
    assert prior_sd > 0.5
    # Defect: the spread is contracted toward m * prior_sd, not preserved.
    assert blended_sd < 0.75 * prior_sd
