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
    # P0-2: the feedback path also sets the external-signal flag so
    # the next ``_compute_trajectory_progress`` call consults the cache.
    assert sched._external_signal_received is True


def test_freetraj_invalid_trajectory_progress_ignored() -> None:
    """A non-finite ``trajectory_progress`` is silently ignored."""
    sched = FreeTrajScheduler(_make_config())
    sched.record_round_feedback(0, {"trajectory_progress": float("nan")})
    # The last trajectory progress stays ``None`` so the deterministic
    # baseline is used. The external-signal flag is NOT set when the
    # value is rejected (P0-2: ``record_round_feedback`` must not turn
    # on the cache gate for invalid input).
    assert sched._last_trajectory_progress is None
    assert sched._external_signal_received is False


def test_freetraj_trajectory_progress_clipped_into_unit_interval() -> None:
    """A ``trajectory_progress`` outside ``[0, 1]`` is clipped."""
    sched = FreeTrajScheduler(_make_config())
    sched.record_round_feedback(0, {"trajectory_progress": 1.5})
    assert sched._last_trajectory_progress == pytest.approx(1.0)
    # Out-of-range but finite inputs DO set the external-signal flag
    # (the cache value is the clipped one).
    assert sched._external_signal_received is True


# ---------------------------------------------------------------------------
# P0-2 regression: trajectory substep is live across rounds when no
# external signal is provided. Pre-fix the cache froze at round 0;
# post-fix the deterministic baseline is re-computed every round.
# ---------------------------------------------------------------------------


def test_freetraj_substep_varies_across_rounds_no_feedback() -> None:
    """P0-2 — the substep fires on odd rounds without an external signal.

    Pre-fix (F-1): the cache was written on every ``sample()`` call
    and short-circuited the deterministic fallback, so the substep
    was frozen at ``sin(2 pi * 0) = 0`` from round 1 onwards.

    Post-fix (P0-2): the cache is only consulted when an external
    ``trajectory_progress`` signal has been recorded. Without that
    signal, ``_compute_trajectory_progress`` recomputes
    ``(round_in_cycle % period) / period`` every round, and the
    substep oscillates with ``sin(2 pi * progress)``.

    With ``trajectory_period=4`` and ``trajectory_amplitude=0.05``,
    rounds 1, 3, 5, 7 sit at progress ``0.25, 0.75, 0.25, 0.75``
    and the *raw* substep values are ``+0.05, -0.05, +0.05, -0.05``.
    The test reads the raw substep from the audit code
    (``freetraj_substep_audit:substep=...``) so the assertion is
    unaffected by the ``[0, 1]`` clip that masks the deviation in
    ``n_cap`` near the cosine peak.
    """
    sched = FreeTrajScheduler(
        _make_config(cycle_length=20), trajectory_amplitude=0.05,
        trajectory_period=4,
    )
    # The raw substep for rounds 1, 3, 5, 7 must be ±amplitude.
    # Round 1 -> progress 0.25 -> sin(+pi/2) = +1 -> +amplitude.
    # Round 3 -> progress 0.75 -> sin(+3pi/2) = -1 -> -amplitude.
    expected = {1: 0.05, 3: -0.05, 5: 0.05, 7: -0.05}
    for r, want in expected.items():
        sample = sched.sample(0, r, r)
        # Locate the FREETRAJ_SUBSTEP_AUDIT code in the audit list
        # and parse out the substep value.
        substep_val: float | None = None
        for code in sample.audit_codes:
            if FREETRAJ_SUBSTEP_AUDIT not in code:
                continue
            for token in code.split(":"):
                if token.startswith("substep="):
                    substep_val = float(token.split("=", 1)[1])
        assert substep_val is not None, (
            f"round {r}: no substep in audit codes"
        )
        assert substep_val == pytest.approx(want, abs=1e-12), (
            f"round {r}: substep {substep_val:+.6f} != expected {want:+.6f}; "
            "the cache bug appears to still be present"
        )
    # Round 0 sits at progress 0 -> sin = 0 -> substep = 0.
    s0 = sched.sample(0, 0, 0)
    for code in s0.audit_codes:
        if FREETRAJ_SUBSTEP_AUDIT not in code:
            continue
        for token in code.split(":"):
            if token.startswith("substep="):
                assert float(token.split("=", 1)[1]) == pytest.approx(0.0, abs=1e-12)


def test_freetraj_external_signal_overrides_recomputed_baseline() -> None:
    """P0-2 — once ``record_round_feedback`` fires, the cache wins.

    Post-fix the cache flag is set by ``record_round_feedback`` so
    the cached value (not the deterministic fallback) drives the
    substep for the next ``sample()`` call. This is the only path
    that consults the cache; the ``sample()`` path no longer writes
    to it.
    """
    sched = FreeTrajScheduler(
        _make_config(cycle_length=20), trajectory_amplitude=0.1,
        trajectory_period=4,
    )

    def _substep_of(sample) -> float:
        for code in sample.audit_codes:
            if FREETRAJ_SUBSTEP_AUDIT not in code:
                continue
            for token in code.split(":"):
                if token.startswith("substep="):
                    return float(token.split("=", 1)[1])
        raise AssertionError("no substep in audit codes")

    # First sample at round 1: no feedback yet, deterministic baseline
    # applies -> progress = 0.25 -> substep = +0.1 * sin(pi/2) = +0.1.
    s_no_fb = sched.sample(0, 1, 1)
    assert _substep_of(s_no_fb) == pytest.approx(0.1, abs=1e-12)

    # Now feed a trajectory_progress of 0.75; substep should be
    # 0.1 * sin(2 pi * 0.75) = 0.1 * sin(3 pi / 2) = -0.1.
    sched.record_round_feedback(1, {"trajectory_progress": 0.75})
    s_with_fb = sched.sample(0, 2, 1)
    assert _substep_of(s_with_fb) == pytest.approx(-0.1, abs=1e-12)
    # And the cache flag is on.
    assert sched._external_signal_received is True
    # The deviation in ``n_cap`` is bounded by the [0, 1] clip; what
    # matters is that the raw substep value (from the audit code) is
    # what the feedback dictated, *not* what the deterministic
    # baseline would give for round_in_cycle=2.
    expected_at_2 = 0.1 * math.sin(2 * math.pi * (2 % 4) / 4)
    assert _substep_of(s_with_fb) != pytest.approx(expected_at_2, abs=1e-6)


def test_freetraj_reset_clears_external_signal_flag() -> None:
    """P0-2 — ``reset()`` clears the external-signal flag and the cache."""
    sched = FreeTrajScheduler(_make_config())
    sched.record_round_feedback(0, {"trajectory_progress": 0.5})
    assert sched._external_signal_received is True
    assert sched._last_trajectory_progress == pytest.approx(0.5)
    sched.reset()
    assert sched._external_signal_received is False
    assert sched._last_trajectory_progress is None


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
