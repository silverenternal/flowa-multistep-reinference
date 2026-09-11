"""Scheduler config round-trip + ScheduleSample.audit_codes tests.

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    ScheduleSample,
    SigmoidScheduler,
    build_scheduler_from_config,
    default_cosine_scheduler,
)


# ---------------------------------------------------------------------------
# from_config / to_config round-trip (P1-1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scheduler",
    [
        default_cosine_scheduler(cycle_length=4, n_min=0.1, n_max=0.9),
        ConstantScheduler(cycle_length=4, n_cap=0.5),
        LinearScheduler(cycle_length=4, n_min=0.0, n_max=1.0),
        ExponentialScheduler(cycle_length=4, n_max=1.0, alpha=0.1),
        PolynomialScheduler(cycle_length=4, n_min=0.0, n_max=1.0, power=2.0),
        SigmoidScheduler(cycle_length=4, n_min=0.0, n_max=1.0, steepness=5.0),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=4, eps_implicit=0.05),
    ],
)
def test_scheduler_config_round_trip(scheduler) -> None:
    """``scheduler == cls.from_config(scheduler.to_config())`` byte-for-byte."""
    config = scheduler.to_config()
    rebuilt = build_scheduler_from_config(config)
    assert type(rebuilt) is type(scheduler)
    assert rebuilt.config_hash() == scheduler.config_hash()
    assert rebuilt.to_config() == config
    # Sample sequence is byte-identical for equal config.
    for r in range(scheduler.cycle_length()):
        s_orig = scheduler.sample(0, r, r)
        s_rebuilt = rebuilt.sample(0, r, r)
        assert s_orig.n_cap == pytest.approx(s_rebuilt.n_cap)


def test_build_scheduler_from_config_dispatches_on_family() -> None:
    """``build_scheduler_from_config`` dispatches on the ``family`` key."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    rebuilt = build_scheduler_from_config(scheduler.to_config())
    assert isinstance(rebuilt, CosineAnnealScheduler)


def test_cosine_scheduler_to_config_has_canonical_keys() -> None:
    """Cosine scheduler's ``to_config`` exposes the canonical keys."""
    scheduler = default_cosine_scheduler(
        cycle_length=4, n_min=0.1, n_max=0.9
    )
    cfg = scheduler.to_config()
    assert cfg["family"] == "cosine"
    assert cfg["schedule_family"] == "cosine_no_restart"
    assert cfg["cycle_length"] == 4
    assert cfg["n_min"] == pytest.approx(0.1)
    assert cfg["n_max"] == pytest.approx(0.9)
    assert "config_hash" in cfg


def test_cosine_scheduler_from_config_round_trip() -> None:
    """``CosineAnnealScheduler.from_config`` matches the constructor."""
    scheduler = default_cosine_scheduler(
        cycle_length=4, n_min=0.1, n_max=0.9
    )
    rebuilt = CosineAnnealScheduler.from_config(scheduler.to_config())
    assert rebuilt.cycle_length() == 4
    assert rebuilt.schedule_family() == "cosine_no_restart"


def test_codimension_scheduler_from_config_ignores_profile() -> None:
    """Codimension round-trip leaves ``profile_residual_fn=None``."""
    profile = lambda x: math.sin(x)  # noqa: E731
    scheduler = CodimensionSheetScheduler(
        cycle_length=4, profile_residual_fn=profile
    )
    rebuilt = CodimensionSheetScheduler.from_config(scheduler.to_config())
    assert rebuilt.profile_residual_fn is None
    assert rebuilt.profile_signature == "default_sheet"


# ---------------------------------------------------------------------------
# P0-A1 — ``audit_codes`` / ``evidence_ratio`` on ``ScheduleSample``
# ---------------------------------------------------------------------------


def test_cosine_sample_carries_audit_codes() -> None:
    """P0-A1: cosine samples carry the family's baseline audit code."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    sample = scheduler.sample(0, 0, 0)
    assert sample.audit_codes == ("cosine_baseline",)
    # The cosine family computes no sheet-vs-cell balance.
    assert sample.evidence_ratio is None


def test_schedule_sample_audit_codes_default_empty() -> None:
    """A bare ``ScheduleSample`` keeps the legacy field set (defaults)."""
    sample = ScheduleSample(
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=0.5,
        n_min=0.0,
        n_max=1.0,
        u_r=0.0,
        family="custom",
        computed_at_round=0,
        schedule_hash="h",
    )
    assert sample.audit_codes == ()
    assert sample.evidence_ratio is None


def test_every_family_emits_audit_codes() -> None:
    """P0-A1 target: 100% of samples carry a non-empty ``audit_codes``."""
    schedulers = [
        default_cosine_scheduler(cycle_length=4),
        ConstantScheduler(cycle_length=4),
        LinearScheduler(cycle_length=4),
        ExponentialScheduler(cycle_length=4),
        PolynomialScheduler(cycle_length=4),
        SigmoidScheduler(cycle_length=4),
        ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=4)
        ),
        CodimensionSheetScheduler(cycle_length=4),
    ]
    total = 0
    tagged = 0
    for scheduler in schedulers:
        for r in range(4):
            sample = scheduler.sample(0, r, r)
            total += 1
            if sample.audit_codes:
                tagged += 1
            assert all(isinstance(c, str) for c in sample.audit_codes)
    assert total == 32
    assert tagged == total


def test_audit_codes_do_not_break_sample_equality() -> None:
    """Two samples from the same scheduler + args still compare equal."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    assert scheduler.sample(0, 2, 2) == scheduler.sample(0, 2, 2)


# ---------------------------------------------------------------------------
# P1-A2 — cosine paper-quantity (A_g) wiring
# ---------------------------------------------------------------------------


def _constant_profile_3(x: float) -> float:
    """Residual profile ``g(x) = 3`` -> ``A_g = 1 / sqrt(10)``."""
    del x
    return 3.0


def test_cosine_paper_quantity_wiring() -> None:
    """P1-A2: ``A_g`` drives the forward-noise mass and raises SNR >= 5%."""
    from adaptive_reflow.contracts import paper_quantities as pq

    baseline = default_cosine_scheduler(cycle_length=4)
    wired = default_cosine_scheduler(
        cycle_length=4, profile_residual_fn=_constant_profile_3
    )
    assert baseline.sheet_A is None
    a_g = float(pq.sheet_evidence_A(_constant_profile_3))
    assert wired.sheet_A == pytest.approx(a_g, rel=1e-12)
    assert a_g == pytest.approx(1.0 / math.sqrt(10.0), rel=1e-6)

    sample = baseline.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros((256, 2), dtype=np.float64)
    base_noise = baseline.inject_noise(
        state, sample, generator=np.random.default_rng(7)
    )
    wired_noise = wired.inject_noise(
        state, sample, generator=np.random.default_rng(7)
    )
    n_cap = float(sample.n_cap)
    assert n_cap > 0.0
    # Same generator stream -> the two outputs differ only by the scale.
    assert wired_noise == pytest.approx(
        base_noise * math.sqrt(a_g / n_cap), rel=1e-12
    )
    # SNR = signal / injected-noise magnitude, so the SNR gain is the
    # inverse ratio of the noise scales.
    snr_gain = math.sqrt(n_cap / a_g) - 1.0
    assert snr_gain >= 0.05

    # The audit trail records the wiring; the unwired path is unchanged.
    wired_codes = wired.sample(0, 0, 0).audit_codes
    assert wired_codes[0] == "cosine_baseline"
    assert any(
        c.startswith("cosine_paper_quantity_wired:") for c in wired_codes
    )
    assert baseline.sample(0, 0, 0).audit_codes == ("cosine_baseline",)


def test_cosine_without_profile_is_byte_identical_legacy() -> None:
    """P1-A2: unwired cosine ``inject_noise`` keeps ``sqrt(n_cap)``."""
    scheduler = default_cosine_scheduler(cycle_length=4)
    sample = scheduler.sample(0, 1, 1).as_cosine_schedule_sample()
    state = np.zeros((64, 2), dtype=np.float64)
    got = scheduler.inject_noise(
        state, sample, generator=np.random.default_rng(3)
    )
    expected = math.sqrt(float(sample.n_cap)) * np.random.default_rng(
        3
    ).standard_normal(state.shape)
    assert np.array_equal(got, expected)


def test_cosine_rejects_non_callable_profile() -> None:
    """A non-callable profile is rejected at construction time."""
    with pytest.raises(ValueError, match="profile_residual_fn"):
        default_cosine_scheduler(
            cycle_length=4,
            profile_residual_fn=1.0,  # type: ignore[arg-type]
        )
