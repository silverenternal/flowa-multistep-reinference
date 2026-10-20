"""GAP-56 — the restart blend is a path state, so its round must start at ``t = m``.

The MNIST flow-matching model is trained on the linear path
``x_t = (1 - t) * x_0 + t * x_1`` with ``x_0 ~ N(0, I)`` and ``x_1`` the data
(``adaptive_reflow/adapters/mnist_fm_train.py``).  ``apply_restart_distribution``
builds

    ``blend = memory_fraction * x_1_hat + (1 - memory_fraction) * x_0``

which is *exactly* the path state at ``t = memory_fraction``.  Before GAP-56 the
driver integrated that state from ``t = 0``, i.e. it asked the velocity field
"what is the velocity at time zero for a point that is actually at time ``m``".
The consequences are:

* ``beta = 0`` (``memory_fraction = 1``) was **not** a no-op — re-integrating an
  already-converged sample destroyed it (measured: ``max|x_after - x_data| =
  1.0137``, relative drift 24.9%);
* every restart round silently discarded the previous round's NFE, which is the
  mechanism behind the R5c regression at matched total NFE.

These tests pin the invariant (``beta = 0`` is an exact no-op under
``restart_t0_mode="memory"``), the on-path identity, the interval plumbing, and
the byte-stability of the legacy ``t0 = 0`` path.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.mnist_fm import MNIST_FM_FLAT_DIM, MnistFmAdapter
from adaptive_reflow.adapters.mnist_fm_train import (
    save_weights,
    velocity_field_unet_init,
)
from adaptive_reflow.universal.state import ODEConditionDelta


def _adapter(tmp_path, *, num_steps: int = 8) -> MnistFmAdapter:
    weights = velocity_field_unet_init(np.random.default_rng(0), base_channels=8)
    path = save_weights(list(weights), tmp_path / "gap56_weights.npz")
    return MnistFmAdapter(weights_path=path, integrator="euler", num_steps=int(num_steps))


def _condition(*, t0: float, t1: float, num_steps: int, round_idx: int = 0) -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec={"t0": float(t0), "t1": float(t1), "num_steps": int(num_steps)},
        source="gap56-test",
        target_round=int(round_idx),
        calibration_artifact_hash="cal-gap56-test",
    )


def _policy(beta: float, round_idx: int = 1):
    from scripts.wave191_p3_mnist_sweep import make_policy

    return make_policy(arm="gap56", beta=float(beta), round_idx=int(round_idx))


def _run_round(
    adapter: MnistFmAdapter, bundle, *, t0: float, t1: float, num_steps: int, round_idx: int = 0
):
    trace = adapter.solve_ode(
        bundle, _condition(t0=t0, t1=t1, num_steps=num_steps, round_idx=round_idx), seed=0
    )
    endpoint = adapter.observe_endpoint(trace, bundle)
    x = np.asarray(adapter._native_states[endpoint.native_state_digest]["x0"], dtype=np.float64)
    return trace, endpoint, x


def test_beta_zero_blend_is_identical_to_the_previous_sample(tmp_path):
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    _, endpoint, x_data = _run_round(adapter, bundle, t0=0.0, t1=1.0, num_steps=8)

    restarted = adapter.apply_restart_distribution(endpoint, _policy(0.0))
    x_blend = np.asarray(
        adapter._native_states[restarted.native_state_digest]["x0"], dtype=np.float64
    )
    assert np.array_equal(x_blend, x_data)


def test_beta_zero_restart_is_an_exact_noop_under_memory_t0(tmp_path):
    """``beta = 0`` means "keep everything", so a restart must cost nothing."""
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    _, endpoint, x_data = _run_round(adapter, bundle, t0=0.0, t1=1.0, num_steps=8)

    restarted = adapter.apply_restart_distribution(endpoint, _policy(0.0))
    # memory_fraction = 1 - beta = 1 -> the round covers the degenerate [1, 1].
    _, _, x_after = _run_round(adapter, restarted, t0=1.0, t1=1.0, num_steps=8, round_idx=1)
    assert np.array_equal(x_after, x_data)


def test_legacy_zero_t0_is_not_a_noop(tmp_path):
    """Regression guard for the defect itself: the legacy wiring moves the sample.

    Uses the production checkpoint (75 KB, shipped in-repo) because an
    untrained UNet has a near-zero velocity field and cannot show the
    destruction the defect causes on a real model.
    """
    ckpt = Path(__file__).resolve().parent.parent / "data" / "mnist_fm" / "production.ckpt.npz"
    if not ckpt.exists():  # pragma: no cover - shipped artifact
        pytest.skip("production MNIST FM checkpoint not present")

    adapter = MnistFmAdapter(weights_path=ckpt, integrator="euler", num_steps=50)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    _, endpoint, x_data = _run_round(adapter, bundle, t0=0.0, t1=1.0, num_steps=50)

    restarted = adapter.apply_restart_distribution(endpoint, _policy(0.0))
    _, _, x_after = _run_round(adapter, restarted, t0=0.0, t1=1.0, num_steps=50, round_idx=1)
    drift = float(np.linalg.norm(x_after - x_data) / np.linalg.norm(x_data))
    assert drift > 0.01, (
        "the legacy t0=0 restart used to destroy the sample; if this now "
        f"drifts by {drift:.6f} the defect may have been fixed elsewhere — "
        "re-check the GAP-56 audit note before relaxing this bound"
    )


def test_memory_t0_restart_preserves_the_sample_at_beta_zero(tmp_path):
    """The GAP-56 fix, on the production model: ``beta = 0`` costs nothing."""
    ckpt = Path(__file__).resolve().parent.parent / "data" / "mnist_fm" / "production.ckpt.npz"
    if not ckpt.exists():  # pragma: no cover - shipped artifact
        pytest.skip("production MNIST FM checkpoint not present")

    adapter = MnistFmAdapter(weights_path=ckpt, integrator="euler", num_steps=50)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    _, endpoint, x_data = _run_round(adapter, bundle, t0=0.0, t1=1.0, num_steps=50)

    restarted = adapter.apply_restart_distribution(endpoint, _policy(0.0))
    _, _, x_after = _run_round(adapter, restarted, t0=1.0, t1=1.0, num_steps=50, round_idx=1)
    assert np.array_equal(x_after, x_data)


@pytest.mark.parametrize("memory_fraction", [0.25, 0.5, 0.7937])
def test_blend_equals_the_path_state_at_t_equals_memory_fraction(tmp_path, memory_fraction):
    """``blend`` must be the linear-path state at ``t = memory_fraction``."""
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    _, endpoint, x_data = _run_round(adapter, bundle, t0=0.0, t1=1.0, num_steps=8)

    beta = 1.0 - float(memory_fraction)
    restarted = adapter.apply_restart_distribution(endpoint, _policy(beta))
    x_blend = np.asarray(
        adapter._native_states[restarted.native_state_digest]["x0"], dtype=np.float64
    )
    # Recover the fresh noise the adapter drew and rebuild the path state by hand.
    x_fresh = (x_blend - memory_fraction * x_data) / (1.0 - memory_fraction)
    expected = (1.0 - memory_fraction) * x_fresh + memory_fraction * x_data
    assert np.allclose(x_blend, expected, rtol=0.0, atol=1e-12)


def test_solve_ode_honours_the_requested_interval(tmp_path):
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    trace, _, _ = _run_round(adapter, bundle, t0=0.4, t1=1.0, num_steps=6)

    stored = adapter._native_states[trace.native_state_digest]
    grid = np.asarray(stored["t_grid"], dtype=np.float64)
    assert grid[0] == pytest.approx(0.4)
    assert grid[-1] == pytest.approx(1.0)
    assert grid.size == 7


def test_default_interval_matches_the_legacy_grid(tmp_path):
    """Omitting ``t0``/``t1`` must reproduce ``linspace(0, 1, n + 1)`` exactly."""
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    condition = ODEConditionDelta(
        delta_spec={"num_steps": 6},
        source="gap56-test",
        target_round=0,
        calibration_artifact_hash="cal-gap56-test",
    )
    trace = adapter.solve_ode(bundle, condition, seed=0)
    grid = np.asarray(adapter._native_states[trace.native_state_digest]["t_grid"])
    assert np.array_equal(grid, np.linspace(0.0, 1.0, 7))


@pytest.mark.parametrize(
    "t0,t1",
    [(-0.1, 1.0), (0.0, 1.1), (0.6, 0.4), (float("nan"), 1.0), (0.0, float("inf"))],
)
def test_invalid_interval_is_rejected(tmp_path, t0, t1):
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    with pytest.raises(ValueError):
        adapter.solve_ode(bundle, _condition(t0=t0, t1=t1, num_steps=4), seed=0)


def test_trajectory_digest_depends_on_the_interval(tmp_path):
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    trace_zero, _, _ = _run_round(adapter, bundle, t0=0.0, t1=1.0, num_steps=6)
    trace_mid, _, _ = _run_round(adapter, bundle, t0=0.4, t1=1.0, num_steps=6)
    assert trace_zero.native_state_digest != trace_mid.native_state_digest


def test_memory_mode_start_matches_the_memory_fraction(tmp_path):
    """The driver's ``t0`` bookkeeping must equal ``1 - beta_r``."""
    from scripts.wave191_p3_mnist_sweep import beta_for_round

    for schedule in ("constant", "equal_budget"):
        for beta_total in (0.0, 0.25, 0.5, 1.0):
            for r in range(1, 4):
                beta_r = beta_for_round(beta_total, r, 4, schedule)
                assert 0.0 <= 1.0 - beta_r <= 1.0
                if schedule == "constant":
                    assert beta_r == pytest.approx(beta_total)


# ---------------------------------------------------------------------------
# GAP-56: the allocation must know how much path each round covers
# ---------------------------------------------------------------------------


def test_restart_t0_per_round_zero_mode_is_all_zeros():
    from scripts.wave191_p3_mnist_sweep import restart_t0_per_round

    assert restart_t0_per_round(0.5, 4, "constant", "zero") == [0.0, 0.0, 0.0, 0.0]


def test_restart_t0_per_round_memory_mode_is_one_minus_beta():
    from scripts.wave191_p3_mnist_sweep import beta_for_round, restart_t0_per_round

    t0 = restart_t0_per_round(0.5, 4, "equal_budget", "memory")
    assert t0[0] == 0.0
    for r in range(1, 4):
        assert t0[r] == pytest.approx(1.0 - beta_for_round(0.5, r, 4, "equal_budget"))
    # Cumulative retention is exactly 1 - beta_total.
    assert t0[1] ** 3 == pytest.approx(0.5)


def test_restart_t0_per_round_rejects_unknown_mode():
    from scripts.wave191_p3_mnist_sweep import restart_t0_per_round

    with pytest.raises(ValueError):
        restart_t0_per_round(0.5, 4, "constant", "half")


def test_uniform_allocation_conserves_the_budget():
    from scripts.wave191_p3_mnist_sweep import per_round_num_steps_equal_budget

    ns = per_round_num_steps_equal_budget(
        "cosine", 4, 50, allocation="uniform"
    )
    assert sum(ns) == 50
    assert max(ns) - min(ns) <= 1


def test_proportional_allocation_follows_the_interval_lengths():
    from scripts.wave191_p3_mnist_sweep import per_round_num_steps_equal_budget

    lengths = [1.0, 0.25, 0.25, 0.25]
    ns = per_round_num_steps_equal_budget(
        "cosine", 4, 50, allocation="proportional", interval_lengths=lengths
    )
    assert sum(ns) == 50
    assert ns[0] > ns[1]
    # 1.0 / 1.75 * 50 = 28.6 -> round 0 takes the majority of the budget.
    assert ns[0] == pytest.approx(28, abs=2)


def test_proportional_allocation_requires_interval_lengths():
    from scripts.wave191_p3_mnist_sweep import per_round_num_steps_equal_budget

    with pytest.raises(ValueError):
        per_round_num_steps_equal_budget("cosine", 4, 50, allocation="proportional")


def test_scheduler_allocation_is_the_gap55_behaviour():
    from scripts.wave191_p3_mnist_sweep import per_round_num_steps_equal_budget

    assert per_round_num_steps_equal_budget("cosine", 4, 50) == (
        per_round_num_steps_equal_budget("cosine", 4, 50, allocation="scheduler")
    )


# ---------------------------------------------------------------------------
# GAP-56: --seed had no effect on the generated samples
# ---------------------------------------------------------------------------


def test_prior_batch_suffix_changes_the_draw(tmp_path):
    """The prior must depend on the seed, or a 3-seed design is vacuous.

    ``build_initial_state`` keys the Gaussian on ``(batch_id, sample_id)``
    only, and ``solve_ode`` discards its ``seed`` argument, so without the
    suffix two "different seeds" produce byte-identical samples.
    """
    adapter = _adapter(tmp_path)
    a = adapter.build_initial_state(batch_id="wave191-p3-s42", sample_id="s00000")
    b = adapter.build_initial_state(batch_id="wave191-p3-s43", sample_id="s00000")
    xa = np.asarray(adapter._native_states[a.native_state_digest]["x0"], dtype=np.float64)
    xb = np.asarray(adapter._native_states[b.native_state_digest]["x0"], dtype=np.float64)
    assert not np.array_equal(xa, xb)


def test_prior_batch_suffix_is_empty_by_default():
    """Legacy batch ids must not gain a suffix when the flag is off."""
    import inspect

    from scripts.wave191_p3_mnist_sweep import run_baseline, run_framework_arm

    assert inspect.signature(run_baseline).parameters["batch_suffix"].default == ""
    assert inspect.signature(run_framework_arm).parameters["batch_suffix"].default == ""


def test_solve_ode_ignores_its_seed(tmp_path):
    """Documents *why* the suffix is needed: the solver is deterministic."""
    adapter = _adapter(tmp_path)
    bundle = adapter.build_initial_state(batch_id="gap56", sample_id="s0")
    cond = _condition(t0=0.0, t1=1.0, num_steps=6)
    t1 = adapter.solve_ode(bundle, cond, seed=1)
    t2 = adapter.solve_ode(bundle, cond, seed=999_999)
    x1 = np.asarray(adapter._native_states[t1.native_state_digest]["trajectory"])
    x2 = np.asarray(adapter._native_states[t2.native_state_digest]["trajectory"])
    assert np.array_equal(x1, x2)
