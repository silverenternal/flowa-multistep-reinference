"""Forward-noise inject_noise tests across all scheduler families (P0-7).

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.algorithm import (
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SigmoidScheduler,
    default_cosine_scheduler,
)


def test_cosine_inject_noise_reproducible_with_seed() -> None:
    """Two identical (state, sample, seed) inputs produce identical output (P0-7)."""
    scheduler = default_cosine_scheduler(cycle_length=8, n_min=0.0, n_max=1.0)
    sample = scheduler.sample(0, 2, 2).as_cosine_schedule_sample()
    state = np.linspace(-1.0, 1.0, 16, dtype=np.float64).reshape(4, 4)

    g1 = np.random.default_rng(42)
    g2 = np.random.default_rng(42)
    out1 = scheduler.inject_noise(state, sample, generator=g1)
    out2 = scheduler.inject_noise(state, sample, generator=g2)

    assert out1.shape == state.shape
    assert np.array_equal(out1, out2)
    assert not np.array_equal(out1, state)


def test_cosine_inject_noise_scales_with_sqrt_n_cap() -> None:
    """inject_noise scales the standard normal by ``sqrt(n_cap)``."""
    scheduler = default_cosine_scheduler(cycle_length=4, n_min=0.0, n_max=1.0)
    state = np.zeros(8, dtype=np.float64)

    sample_low = scheduler.sample(0, 3, 3).as_cosine_schedule_sample()
    sample_high = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()

    gen_low = np.random.default_rng(7)
    gen_high = np.random.default_rng(7)
    out_low = scheduler.inject_noise(state, sample_low, generator=gen_low)
    out_high = scheduler.inject_noise(state, sample_high, generator=gen_high)
    # ``n_cap`` near 0.0 at round 3 -> near-zero noise; at round 0 -> max noise.
    assert np.std(out_low) < np.std(out_high)


@pytest.mark.parametrize(
    "scheduler_factory",
    [
        CosineAnnealScheduler,
        ConstantScheduler,
        LinearScheduler,
        ExponentialScheduler,
        PolynomialScheduler,
        SigmoidScheduler,
    ],
)
def test_every_scheduler_implements_inject_noise(scheduler_factory) -> None:
    """Every SchedulerProtocol implementation exposes ``inject_noise``."""
    if scheduler_factory is CosineAnnealScheduler:
        scheduler = default_cosine_scheduler(cycle_length=4)
    elif scheduler_factory is ConstantScheduler:
        scheduler = ConstantScheduler(cycle_length=4, n_cap=0.5)
    elif scheduler_factory is LinearScheduler:
        scheduler = LinearScheduler(cycle_length=4, n_min=0.0, n_max=1.0)
    elif scheduler_factory is ExponentialScheduler:
        scheduler = ExponentialScheduler(cycle_length=4)
    elif scheduler_factory is PolynomialScheduler:
        scheduler = PolynomialScheduler(cycle_length=4, power=2.0)
    elif scheduler_factory is SigmoidScheduler:
        scheduler = SigmoidScheduler(cycle_length=4)
    else:  # pragma: no cover
        raise AssertionError("unhandled factory")
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    out = scheduler.inject_noise(state, sample, generator=gen)
    assert out.shape == state.shape
    assert np.all(np.isfinite(out))


def test_codimension_scheduler_inject_noise_uses_A_g_when_available() -> None:
    """The codimension scheduler uses ``sheet_A`` as the noise mass when set."""
    import math

    profile = lambda x: math.sin(x)  # noqa: E731
    scheduler = CodimensionSheetScheduler(
        cycle_length=4,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
        eps_implicit=0.05,
    )
    assert scheduler.sheet_A is not None
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    out = scheduler.inject_noise(state, sample, generator=gen)
    assert out.shape == state.shape
    assert np.all(np.isfinite(out))


def test_convergence_adaptive_inject_noise_delegates_to_base() -> None:
    """The adaptive scheduler's ``inject_noise`` delegates to its base."""
    scheduler = ConvergenceAdaptiveScheduler()
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen_a = np.random.default_rng(123)
    gen_b = np.random.default_rng(123)
    out_adaptive = scheduler.inject_noise(state, sample, generator=gen_a)
    out_base = scheduler.base.inject_noise(state, sample, generator=gen_b)
    assert np.array_equal(out_adaptive, out_base)
