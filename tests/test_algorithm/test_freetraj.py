"""Tests for :class:`FreeTrajScheduler` (A1 — FreeTraj, arXiv:2507.10532).

The scheduler wraps a :class:`CosineAnnealScheduler` baseline and
applies a small trajectory-aware additive offset
``amplitude * sin(2 pi * progress)``. The tests cover:

* construction + identity (``schedule_family``, ``config_hash``);
* the cosine baseline is preserved when ``trajectory_amplitude=0``;
* the trajectory substep oscillates around the baseline as
  ``round_in_cycle`` cycles through the trajectory period;
* :meth:`record_round_feedback` overrides the deterministic progress
  with a feedback-supplied ``trajectory_progress``;
* the ``to_config`` / ``from_config`` round-trip.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.scheduler import (
    FREETRAJ_SUBSTEP_AUDIT,
    FreeTrajScheduler,
    SchedulerProtocol,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleConfig,
    FactorValue,
)


def _make_config(
    *, cycle_length: int = 20, n_min: float = 0.0, n_max: float = 1.0,
) -> CosineScheduleConfig:
    return CosineScheduleConfig(
        cycle_length=cycle_length,
        n_min=FactorValue(n_min),
        n_max=FactorValue(n_max),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("freetraj_test"),
        frozen_before_evaluation=True,
    )


# ---------------------------------------------------------------------------
# Construction + identity
# ---------------------------------------------------------------------------


def test_freetraj_is_a_scheduler_protocol() -> None:
    """``FreeTrajScheduler`` conforms to :class:`SchedulerProtocol`."""
    sched = FreeTrajScheduler(_make_config())
    assert isinstance(sched, SchedulerProtocol)


def test_freetraj_family_is_freetraj() -> None:
    """``schedule_family`` returns ``"freetraj"``."""
    sched = FreeTrajScheduler(_make_config())
    assert sched.schedule_family() == "freetraj"


def test_freetraj_config_hash_stable() -> None:
    """Two schedulers with the same config have the same ``config_hash``."""
    a = FreeTrajScheduler(_make_config())
    b = FreeTrajScheduler(_make_config())
    assert a.config_hash() == b.config_hash()


def test_freetraj_cycle_length_matches_config() -> None:
    """``cycle_length`` returns the configured cycle length."""
    sched = FreeTrajScheduler(_make_config(cycle_length=12))
    assert sched.cycle_length() == 12


def test_freetraj_rejects_invalid_amplitude() -> None:
    """``trajectory_amplitude`` outside ``[0, 1]`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        FreeTrajScheduler(_make_config(), trajectory_amplitude=-0.1)
    with pytest.raises(ValueError):
        FreeTrajScheduler(_make_config(), trajectory_amplitude=1.5)


def test_freetraj_rejects_invalid_period() -> None:
    """``trajectory_period < 1`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        FreeTrajScheduler(_make_config(), trajectory_period=0)


# ---------------------------------------------------------------------------
# Cosine baseline + trajectory substep
# ---------------------------------------------------------------------------


def test_freetraj_zero_amplitude_matches_cosine_baseline() -> None:
    """``trajectory_amplitude=0`` produces the cosine baseline exactly."""
    sched = FreeTrajScheduler(_make_config(), trajectory_amplitude=0.0)
    for r in range(5):
        sample = sched.sample(0, r, r)
        assert math.isfinite(sample.n_cap)
        assert 0.0 <= sample.n_cap <= 1.0


def test_freetraj_substep_oscillates_within_amplitude() -> None:
    """``|n_cap - baseline| <= trajectory_amplitude`` for every round."""
    amplitude = 0.1
    sched = FreeTrajScheduler(
        _make_config(), trajectory_amplitude=amplitude, trajectory_period=4,
    )
    # Build a baseline scheduler for comparison.
    from adaptive_reflow.algorithm.scheduler import default_cosine_scheduler

    baseline = default_cosine_scheduler(
        cycle_length=20, n_min=0.0, n_max=1.0,
        schedule_family="cosine_no_restart", seed=0,
    )
    for r in range(8):
        freetraj_sample = sched.sample(0, r, r)
        baseline_sample = baseline.sample(0, r, r)
        delta = abs(freetraj_sample.n_cap - baseline_sample.n_cap)
        assert delta <= amplitude + 1e-9


def test_freetraj_sample_includes_substep_audit_code() -> None:
    """The sample's audit codes include the trajectory substep audit."""
    sched = FreeTrajScheduler(
        _make_config(), trajectory_amplitude=0.05, trajectory_period=4,
    )
    sample = sched.sample(0, 0, 0)
    assert any(FREETRAJ_SUBSTEP_AUDIT in c for c in sample.audit_codes)


def test_freetraj_round_zero_n_cap_close_to_n_max() -> None:
    """At round 0 with ``n_max=1.0`` the cosine baseline dominates."""
    sched = FreeTrajScheduler(_make_config(), trajectory_amplitude=0.0)
    sample = sched.sample(0, 0, 0)
    assert math.isclose(sample.n_cap, 1.0, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Feedback override
# ---------------------------------------------------------------------------


def test_freetraj_feedback_overrides_trajectory_progress() -> None:
    """``metrics['trajectory_progress']`` overrides the deterministic baseline."""
    sched = FreeTrajScheduler(
        _make_config(), trajectory_amplitude=0.1, trajectory_period=4,
    )
    sched.record_round_feedback(0, {"trajectory_progress": 0.25})
    assert sched._last_trajectory_progress == pytest.approx(0.25)


def test_freetraj_invalid_trajectory_progress_ignored() -> None:
    """A non-finite ``trajectory_progress`` is silently ignored."""
    sched = FreeTrajScheduler(_make_config())
    sched.record_round_feedback(0, {"trajectory_progress": float("nan")})
    # The last trajectory progress stays ``None`` so the deterministic
    # baseline is used.
    assert sched._last_trajectory_progress is None


def test_freetraj_trajectory_progress_clipped_into_unit_interval() -> None:
    """A ``trajectory_progress`` outside ``[0, 1]`` is clipped."""
    sched = FreeTrajScheduler(_make_config())
    sched.record_round_feedback(0, {"trajectory_progress": 1.5})
    assert sched._last_trajectory_progress == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Reset + config round-trip
# ---------------------------------------------------------------------------


def test_freetraj_reset_clears_state() -> None:
    """``reset()`` clears the last sample + trajectory progress."""
    sched = FreeTrajScheduler(_make_config())
    sched.sample(0, 0, 0)
    sched.record_round_feedback(0, {"trajectory_progress": 0.5})
    sched.reset()
    assert sched.last_sample is None
    assert sched._last_trajectory_progress is None


def test_freetraj_to_config_returns_dict() -> None:
    """``to_config`` includes the ``"family": "freetraj"`` key."""
    sched = FreeTrajScheduler(
        _make_config(), trajectory_amplitude=0.07, trajectory_period=6,
    )
    config = sched.to_config()
    assert config["family"] == "freetraj"
    assert config["trajectory_amplitude"] == pytest.approx(0.07)
    assert config["trajectory_period"] == 6


def test_freetraj_from_config_round_trip() -> None:
    """``from_config`` reproduces a byte-identical scheduler."""
    original = FreeTrajScheduler(
        _make_config(), trajectory_amplitude=0.08, trajectory_period=3,
    )
    rebuilt = FreeTrajScheduler.from_config(original.to_config())
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.trajectory_amplitude == pytest.approx(0.08)
    assert rebuilt.trajectory_period == 3


def test_freetraj_from_config_rejects_non_dict() -> None:
    """``from_config`` fails closed on non-dict input."""
    with pytest.raises(TypeError):
        FreeTrajScheduler.from_config("not_a_dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Inject noise (forwards to wrapped cosine)
# ---------------------------------------------------------------------------


def test_freetraj_inject_noise_is_reproducible() -> None:
    """``inject_noise`` is byte-deterministic for a fixed seed."""
    import numpy as np

    sched = FreeTrajScheduler(_make_config())
    sample = sched.sample(0, 0, 0)
    state = np.zeros(2, dtype=np.float64)
    out_a = sched.inject_noise(state, sample.as_cosine_schedule_sample(),
                                generator=np.random.default_rng(42))
    out_b = sched.inject_noise(state, sample.as_cosine_schedule_sample(),
                                generator=np.random.default_rng(42))
    assert np.array_equal(out_a, out_b)
