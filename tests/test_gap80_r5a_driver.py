"""GAP-80 §8 — the restart-capable R5a driver.

Pre-registration: ``docs/audit/gap80-r5a-harness.md`` §8. These tests pin the
driver's contract, not its numbers: NFE conservation, the restart dispatch
count, and the fact that the two seeding conventions produce different
populations while the baseline arm does not restart at all.
"""

from __future__ import annotations

import numpy as np

from tools.r5a_restart_driver import (
    _solve_one,
    _split_nfe,
    _trace_cov,
    run_protocol_arm,
)


def test_nfe_split_conserves_the_budget() -> None:
    for total, rounds in ((150, 5), (150, 4), (10, 3), (7, 5)):
        parts = _split_nfe(total, rounds)
        assert len(parts) == rounds
        assert sum(parts) == total
        assert parts[-1] >= parts[0]


def test_baseline_arm_dispatches_no_restart() -> None:
    """The control is one pass: no restart, whatever the round count."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from tools.eval.baseline import _build_initial_state_and_condition

    class _Counting(TwoDimFMAdapter):
        def __init__(self, **kw: object) -> None:
            super().__init__(**kw)  # type: ignore[arg-type]
            self.restarts = 0

        def apply_restart_distribution(self, state, policy):  # noqa: ANN001
            self.restarts += 1
            return super().apply_restart_distribution(state, policy)

    adapter = _Counting(target="two_moons")
    bundle, _ = _build_initial_state_and_condition(
        adapter, seed=1, nfe=20, batch_id="b", sample_id="s"
    )
    _solve_one(
        adapter,
        bundle,
        seed=1,
        nfe=20,
        n_rounds=1,
        betas=None,
        restart=False,
    )
    assert adapter.restarts == 0


def test_restart_arm_dispatches_once_per_gap() -> None:
    """``n_rounds = 5`` restarts after rounds 0..3, never after the last."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from tools.eval.baseline import _build_initial_state_and_condition

    class _Counting(TwoDimFMAdapter):
        def __init__(self, **kw: object) -> None:
            super().__init__(**kw)  # type: ignore[arg-type]
            self.restarts = 0

        def apply_restart_distribution(self, state, policy):  # noqa: ANN001
            self.restarts += 1
            return super().apply_restart_distribution(state, policy)

    adapter = _Counting(target="two_moons")
    bundle, _ = _build_initial_state_and_condition(
        adapter, seed=1, nfe=20, batch_id="b", sample_id="s"
    )
    _solve_one(
        adapter,
        bundle,
        seed=1,
        nfe=20,
        n_rounds=5,
        betas=[0.1, 0.2, 0.3, 0.4, 0.5],
        restart=True,
    )
    assert adapter.restarts == 4


def test_record_scope_changes_the_fresh_draw() -> None:
    """A record-scoped policy hash gives each record a different restart."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from tools.eval.baseline import _build_initial_state_and_condition

    def _first_restart_point(record_key: str) -> np.ndarray:
        adapter = TwoDimFMAdapter(target="two_moons")
        bundle, _ = _build_initial_state_and_condition(
            adapter, seed=3, nfe=20, batch_id="b", sample_id="s"
        )
        return _solve_one(
            adapter,
            bundle,
            seed=3,
            nfe=20,
            n_rounds=5,
            betas=[1.0, 1.0, 1.0, 1.0, 1.0],  # beta = 1 -> pure fresh draw
            restart=True,
            record_key=record_key,
        )

    shared = _first_restart_point("")
    a = _first_restart_point("seed-0")
    b = _first_restart_point("seed-1")
    assert not np.allclose(a, b), "record scope must break the shared draw"
    # The record-scoped draw still has to be reproducible for a fixed key.
    assert np.allclose(a, _first_restart_point("seed-0"))
    assert shared.shape == a.shape == (2,)


def test_protocol_arm_is_deterministic() -> None:
    kw = dict(seed=5, n_records=8, nfe=20, n_rounds=3, restart=True)
    first = run_protocol_arm(**kw)  # type: ignore[arg-type]
    second = run_protocol_arm(**kw)  # type: ignore[arg-type]
    assert np.array_equal(first, second)


def test_trace_cov_is_the_sum_of_axis_variances() -> None:
    x = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    # ddof=1 -> var(x) = 1.0, var(y) = 0.0
    assert np.isclose(_trace_cov(x), 1.0)


def test_convex_helper_reproduces_the_adapter_byte_for_byte() -> None:
    """The driver's convex blend must be the adapter's operator, not a copy
    that drifted. This is what licenses reading ``vp_record`` as "the same
    restart with a different variance rule"."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from tools.eval.baseline import _build_initial_state_and_condition
    from tools.eval.framework import _make_framework_policy
    from tools.r5a_restart_driver import _bundle_after_restart, _restart_point

    adapter = TwoDimFMAdapter(target="two_moons")
    bundle, _ = _build_initial_state_and_condition(
        adapter, seed=9, nfe=20, batch_id="b", sample_id="s"
    )
    policy = _make_framework_policy(
        adapter, target_round=0, seed=9, nfe=0, beta_override=0.4
    )
    ref = adapter.apply_restart_distribution(bundle, policy)
    ref_x0 = np.asarray(
        adapter._native_states[ref.native_state_digest]["x0"], dtype=np.float64
    )

    blended, beta, memory = _restart_point(
        adapter, bundle, policy, mode="convex"
    )
    got = _bundle_after_restart(
        adapter, bundle, policy, blended, beta=beta, memory=memory
    )
    got_x0 = np.asarray(
        adapter._native_states[got.native_state_digest]["x0"], dtype=np.float64
    )
    assert np.array_equal(ref_x0, got_x0)
    assert ref.native_state_digest == got.native_state_digest
    assert ref.source_round == got.source_round


def test_vp_restart_preserves_the_input_variance() -> None:
    """``m * prior + sqrt(1 - m^2) * fresh`` keeps Var = 1 for unit inputs."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from tools.eval.baseline import _build_initial_state_and_condition
    from tools.eval.framework import _make_framework_policy
    from tools.r5a_restart_driver import _restart_point

    adapter = TwoDimFMAdapter(target="two_moons")
    bundle, _ = _build_initial_state_and_condition(
        adapter, seed=11, nfe=20, batch_id="b", sample_id="s"
    )
    for beta in (0.2, 0.5, 0.8):
        policy = _make_framework_policy(
            adapter, target_round=0, seed=11, nfe=0, beta_override=beta
        )
        vp, _, _ = _restart_point(adapter, bundle, policy, mode="vp")
        convex, _, _ = _restart_point(adapter, bundle, policy, mode="convex")
        # Both start from the same prior and the same fresh draw, so the two
        # points differ by exactly the coefficient on the fresh term.
        prior = np.asarray(
            adapter._native_states[bundle.native_state_digest]["x0"],
            dtype=np.float64,
        )
        m = 1.0 - beta
        fresh_vp = (vp - m * prior) / max(1e-12, np.sqrt(max(0.0, 1.0 - m * m)))
        fresh_cv = (convex - m * prior) / max(1e-12, 1.0 - m)
        assert np.allclose(fresh_vp, fresh_cv)


def test_default_interval_is_byte_identical() -> None:
    """Omitting ``t0`` and passing ``t0 = 0.0`` must agree exactly."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.universal.state import ODEConditionDelta

    def _run(with_t0: bool):
        adapter = TwoDimFMAdapter(target="two_moons")
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        spec = {"num_steps": 12, "sampler_id": "euler"}
        if with_t0:
            spec["t0"] = 0.0
            spec["t1"] = 1.0
        trace = adapter.solve_ode(
            bundle,
            ODEConditionDelta(
                delta_spec=spec,
                source="test",
                target_round=0,
                calibration_artifact_hash="test:1",
            ),
            seed=1,
        )
        return trace.native_state_digest, adapter._native_states[
            trace.native_state_digest
        ]["trajectory"]

    d0, traj0 = _run(False)
    d1, traj1 = _run(True)
    assert d0 == d1
    assert np.array_equal(traj0, traj1)


def test_non_default_interval_changes_the_trajectory_and_digest() -> None:
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.universal.state import ODEConditionDelta

    def _run(t0: float):
        adapter = TwoDimFMAdapter(target="two_moons")
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        trace = adapter.solve_ode(
            bundle,
            ODEConditionDelta(
                delta_spec={"num_steps": 12, "sampler_id": "euler", "t0": t0},
                source="test",
                target_round=1,
                calibration_artifact_hash="test:1",
            ),
            seed=1,
        )
        entry = adapter._native_states[trace.native_state_digest]
        return trace.native_state_digest, entry["trajectory"], entry["t_grid"]

    d0, traj0, grid0 = _run(0.0)
    d5, traj5, grid5 = _run(0.5)
    assert d0 != d5
    assert not np.allclose(traj0, traj5)
    assert np.isclose(grid0[0], 0.0) and np.isclose(grid5[0], 0.5)
    assert np.isclose(grid5[-1], 1.0)
    # the step count is preserved, so the NFE budget does not move
    assert grid0.shape == grid5.shape
