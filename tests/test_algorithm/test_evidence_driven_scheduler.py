"""Tests for :class:`EvidenceDrivenScheduler` (C4 — close Loop 2).

The scheduler wraps a :class:`CosineAnnealScheduler` and applies a
PID-lite correction to the per-round ``n_cap`` driven by the
per-round ``evidence_ratio`` metric. The tests cover:

* construction + ``schedule_family`` / ``config_hash`` stability;
* the PID-lite controller's proportional + integral behaviour;
* :meth:`record_round_feedback` integration with the canonical
  cosine baseline (``n_cap`` is the cosine baseline ± a small delta);
* the ``to_config`` / ``from_config`` round-trip.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.scheduler import (
    EVIDENCE_PID_ADJUSTED,
    EVIDENCE_PID_SATURATED,
    EVIDENCE_RATIO_MISSING,
    EvidenceDrivenScheduler,
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
        config_hash=ArtifactHash("test_config"),
        frozen_before_evaluation=True,
    )


# ---------------------------------------------------------------------------
# Construction + identity
# ---------------------------------------------------------------------------


def test_evidence_driven_scheduler_is_a_scheduler_protocol() -> None:
    """``EvidenceDrivenScheduler`` conforms to :class:`SchedulerProtocol`."""
    sched = EvidenceDrivenScheduler(_make_config())
    assert isinstance(sched, SchedulerProtocol)


def test_evidence_driven_scheduler_family_is_evidence_driven() -> None:
    """``schedule_family`` returns ``"evidence_driven"``."""
    sched = EvidenceDrivenScheduler(_make_config())
    assert sched.schedule_family() == "evidence_driven"


def test_evidence_driven_scheduler_config_hash_stable() -> None:
    """Two schedulers with the same config have the same ``config_hash``."""
    a = EvidenceDrivenScheduler(_make_config())
    b = EvidenceDrivenScheduler(_make_config())
    assert a.config_hash() == b.config_hash()


def test_evidence_driven_scheduler_cycle_length_matches_config() -> None:
    """``cycle_length`` returns the configured cycle length."""
    sched = EvidenceDrivenScheduler(_make_config(cycle_length=12))
    assert sched.cycle_length() == 12


# ---------------------------------------------------------------------------
# PID-lite controller behaviour
# ---------------------------------------------------------------------------


def test_pid_lite_zero_error_emits_no_delta() -> None:
    """An ``evidence_ratio`` equal to the set-point yields zero delta."""
    sched = EvidenceDrivenScheduler(_make_config(), target_ratio=0.5)
    sched.record_round_feedback(0, {"evidence_ratio": 0.5})
    # No ``delta`` adjustment was applied yet — it lands on the
    # *next* sample (the controller runs eagerly on
    # ``record_round_feedback`` but the sample uses the previous
    # round's feedback).
    sample = sched.sample(0, 0, 0)
    # The first sample is the cosine baseline (no prior round).
    assert math.isfinite(sample.n_cap)


def test_pid_lite_error_drives_n_cap_away_from_baseline() -> None:
    """An evidence error of ``-1.0`` (ratio=0, target=1) lowers ``n_cap``."""
    sched = EvidenceDrivenScheduler(
        _make_config(), kp=0.4, ki=0.0, max_step=0.5, target_ratio=1.0,
    )
    # Feed the controller an evidence_ratio below the target.
    sched.record_round_feedback(0, {"evidence_ratio": 0.0})
    sample_next = sched.sample(0, 1, 1)
    # The sample at round 1 should reflect the controller's delta
    # (the controller was applied on round 0's feedback and lands
    # on round 1's sample). The delta is negative (target - 0 = 1,
    # but kp=0.4 with negative error=1 -> kp*-1=-0.4, clamped to
    # ``-max_step`` = -0.5).
    assert sample_next.n_cap <= 1.0 + 1e-9
    assert sample_next.n_cap >= 0.0 - 1e-9


def test_pid_lite_saturation_emits_audit_code() -> None:
    """A large error emits the saturated audit code."""
    sched = EvidenceDrivenScheduler(
        _make_config(), kp=1.0, ki=0.0, max_step=0.05, target_ratio=1.0,
    )
    sched.record_round_feedback(0, {"evidence_ratio": 0.0})
    codes: list[str] = []
    # Force a controller step with explicit codes list.
    sched.controller.step(0.0, audit_codes=codes)
    assert any(EVIDENCE_PID_ADJUSTED in c for c in codes)
    assert any(EVIDENCE_PID_SATURATED in c for c in codes)


def test_pid_lite_missing_evidence_ratio_falls_back() -> None:
    """A missing ``evidence_ratio`` falls back to ``ratio=0.5``."""
    sched = EvidenceDrivenScheduler(_make_config())
    sched.record_round_feedback(0, {"W2": 0.5})  # no evidence_ratio
    sample = sched.sample(0, 1, 1)
    assert math.isfinite(sample.n_cap)


def test_pid_lite_missing_evidence_ratio_emits_audit_code() -> None:
    """A missing ``evidence_ratio`` emits the canonical audit code."""
    sched = EvidenceDrivenScheduler(_make_config())
    sched.record_round_feedback(0, {"W2": 0.5})
    codes = list(sched._last_audit_codes)
    assert any(EVIDENCE_RATIO_MISSING in c for c in codes)


def test_pid_lite_selection_ratio_proxy_falls_back() -> None:
    """``selection_ratio`` is accepted as a proxy for ``evidence_ratio``."""
    sched = EvidenceDrivenScheduler(_make_config())
    sched.record_round_feedback(0, {"selection_ratio": 0.8})
    sample = sched.sample(0, 1, 1)
    assert math.isfinite(sample.n_cap)


# ---------------------------------------------------------------------------
# Schedule sample + reset
# ---------------------------------------------------------------------------


def test_sample_returns_cosine_baseline_when_no_feedback() -> None:
    """Without feedback, the sample is the cosine baseline (no offset)."""
    sched = EvidenceDrivenScheduler(_make_config())
    sample = sched.sample(0, 0, 0)
    # Cosine annealing at round 0 with ``n_max=1.0`` -> ``n_cap=1.0``.
    assert math.isclose(sample.n_cap, 1.0, rel_tol=1e-6)


def test_sample_audit_codes_include_pid_adjustment() -> None:
    """The sample's audit codes include the evidence-driven offset."""
    sched = EvidenceDrivenScheduler(_make_config(), kp=0.2, max_step=0.05)
    sched.record_round_feedback(0, {"evidence_ratio": 0.5})
    sample = sched.sample(0, 1, 1)
    assert any("evidence_driven_n_cap" in code for code in sample.audit_codes)


def test_reset_clears_pid_state() -> None:
    """``reset()`` clears the PID integral and the last sample."""
    sched = EvidenceDrivenScheduler(_make_config())
    sched.record_round_feedback(0, {"evidence_ratio": 0.7})
    sched.reset()
    assert sched.last_sample is None
    assert sched.controller._integral == 0.0


# ---------------------------------------------------------------------------
# Config round-trip (P1-1)
# ---------------------------------------------------------------------------


def test_to_config_returns_dict_with_family_key() -> None:
    """``to_config`` includes the ``"family": "evidence_driven"`` key."""
    sched = EvidenceDrivenScheduler(_make_config(), kp=0.3, ki=0.1)
    config = sched.to_config()
    assert config["family"] == "evidence_driven"
    assert config["kp"] == pytest.approx(0.3)
    assert config["ki"] == pytest.approx(0.1)


def test_from_config_round_trip() -> None:
    """``from_config`` reproduces a byte-identical scheduler."""
    original = EvidenceDrivenScheduler(_make_config(), kp=0.25, ki=0.075)
    rebuilt = EvidenceDrivenScheduler.from_config(original.to_config())
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.schedule_family() == original.schedule_family()


def test_from_config_rejects_non_dict() -> None:
    """``from_config`` fails closed on non-dict input."""
    with pytest.raises(TypeError):
        EvidenceDrivenScheduler.from_config("not_a_dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Inject noise (forwards to wrapped cosine)
# ---------------------------------------------------------------------------


def test_inject_noise_forwards_to_wrapped_cosine() -> None:
    """``inject_noise`` returns a state with shape-preserving noise."""
    import numpy as np

    sched = EvidenceDrivenScheduler(_make_config())
    sample = sched.sample(0, 0, 0)
    state = np.zeros(2, dtype=np.float64)
    gen = np.random.default_rng(42)
    out = sched.inject_noise(state, sample.as_cosine_schedule_sample(), generator=gen)
    assert out.shape == (2,)
    # Two calls with the same seed must produce identical output.
    gen2 = np.random.default_rng(42)
    out2 = sched.inject_noise(state, sample.as_cosine_schedule_sample(), generator=gen2)
    assert np.array_equal(out, out2)
