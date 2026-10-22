"""GAP-74 — default-off ``restart_t0`` override on the MNIST adapter.

Pre-registration: ``docs/audit/gap74-conditional-mean-bound.md`` §0. The
override exists so the conditional-mean sweep can vary ``m`` at a **fixed**
``t0``; today the design ties ``t0 = 1 - beta``, which confounds the deviation
channel with the integration-length channel.

Round 0 must keep ``t0 = 0``: it has no preceding endpoint, so integrating the
initial Gaussian from mid-path would be a different experiment.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
from adaptive_reflow.universal import ODEConditionDelta


def _adapter(**kwargs: object) -> MnistFmAdapter:
    return MnistFmAdapter(
        init_random_weights=True,
        base_channels=8,
        num_steps=4,
        **kwargs,
    )


def _condition(t0: float, *, target_round: int) -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec={"t0": float(t0), "t1": 1.0, "num_steps": 4},
        source="gap74-test",
        target_round=int(target_round),
        calibration_artifact_hash="cal-gap74",
    )


def _t_grid(adapter: MnistFmAdapter, condition: ODEConditionDelta) -> np.ndarray:
    """Return the integration grid actually used for ``condition``.

    The endpoint cloud saturates against ``MNIST_FM_CLAMP`` with random-init
    weights, so comparing endpoints cannot see a ``t0`` change. The stored
    ``t_grid`` is the direct evidence that the override reached the integrator.
    """
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    trace = adapter.solve_ode(bundle, condition, seed=7)
    return np.asarray(
        adapter._native_states.get(trace.native_state_digest)["t_grid"],
        dtype=np.float64,
    )


# ---------------------------------------------------------------------------
# 1. default off
# ---------------------------------------------------------------------------


def test_default_keeps_the_driver_supplied_t0() -> None:
    """``restart_t0=None`` must leave ``delta_spec["t0"]`` in charge."""
    plain = _adapter()
    assert plain._restart_t0 is None
    grid = _t_grid(plain, _condition(0.4, target_round=1))
    assert grid[0] == pytest.approx(0.4)
    assert grid[-1] == pytest.approx(1.0)


def test_override_applies_to_restart_rounds_only() -> None:
    """Round 0 keeps ``t0 = 0``; a restart round is pinned to the override."""
    plain = _adapter()
    pinned = _adapter(restart_t0=0.75)

    round0 = _condition(0.0, target_round=0)
    assert _t_grid(plain, round0)[0] == pytest.approx(0.0)
    assert _t_grid(pinned, round0)[0] == pytest.approx(0.0)

    restart = _condition(0.4, target_round=1)
    assert _t_grid(plain, restart)[0] == pytest.approx(0.4)
    assert _t_grid(pinned, restart)[0] == pytest.approx(0.75)


def test_override_is_deterministic() -> None:
    pinned = _adapter(restart_t0=0.5)
    cond = _condition(0.2, target_round=2)
    np.testing.assert_array_equal(_t_grid(pinned, cond), _t_grid(pinned, cond))


# ---------------------------------------------------------------------------
# 2. validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan"), float("inf")])
def test_invalid_restart_t0_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="restart_t0_must_be_finite_in"):
        _adapter(restart_t0=bad)


# ---------------------------------------------------------------------------
# 3. driver-side schedule helper
# ---------------------------------------------------------------------------


def test_restart_t0_per_round_fixed_pins_every_restart_round() -> None:
    from scripts.wave191_p3_mnist_sweep import restart_t0_per_round

    assert restart_t0_per_round(0.5, 3, "equal_budget", "memory", fixed_t0=0.5) == [
        0.0,
        0.5,
        0.5,
    ]
    # Round 0 is always 0 regardless of the override.
    assert restart_t0_per_round(0.9, 4, "constant", "zero", fixed_t0=0.25) == [
        0.0,
        0.25,
        0.25,
        0.25,
    ]


def test_restart_t0_per_round_default_is_unchanged() -> None:
    from scripts.wave191_p3_mnist_sweep import restart_t0_per_round

    assert restart_t0_per_round(0.5, 3, "constant", "zero") == [0.0, 0.0, 0.0]
    memory = restart_t0_per_round(0.5, 3, "constant", "memory")
    assert memory[0] == 0.0 and memory[1] == pytest.approx(0.5)


@pytest.mark.parametrize("bad", [-0.2, 1.2, float("nan")])
def test_restart_t0_per_round_rejects_out_of_range(bad: float) -> None:
    from scripts.wave191_p3_mnist_sweep import restart_t0_per_round

    with pytest.raises(ValueError, match="fixed_t0_must_be_finite_in"):
        restart_t0_per_round(0.5, 3, "constant", "memory", fixed_t0=bad)
