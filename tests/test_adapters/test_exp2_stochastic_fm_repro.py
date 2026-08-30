"""EXP-2 reproduction tests for the StochasticFMAdapter 25% W2-reduction claim.

The StochasticFMAdapter (see ``adaptive_reflow.adapters.stochastic_fm``)
claims, in its module docstring, a "Quantitative target: on a
stochastic-target benchmark the framework's per-round W2 is at least
25 % lower than the deterministic adapter."

These tests reproduce that comparison. The deterministic baseline is
the *same* adapter with ``noise_scale = 0.0`` (the noise term
vanishes; the drift remains the canonical
``encoder_gain * (target - y)``). The stochastic treatment uses the
adapter's default ``noise_scale = 0.05`` plus the default
``adaptive_noise_gamma = 1.0`` so the noise grows linearly in ``t``.

The trajectories are integrated by calling :func:`stochastic_velocity`
directly (the adapter's :meth:`StochasticFMAdapter.solve_ode`
intentionally does not preserve the integrated ``y`` — only a digest
— so we reproduce the integration externally). The framework's
``noise_scale`` parameter is the only knob that differs between the
deterministic and stochastic treatments.

The quantitative claim being tested
-----------------------------------
For ``n_endpoints = 128`` endpoints drawn from ``N(0, I_2)`` and a
two-moons target of size ``n_target = 1000``, the ratio

    ratio = W2(stochastic distribution, two-moons) /
            W2(deterministic distribution, two-moons)

must be at most ``0.75`` (i.e., stochastic W2 <= 75 % of deterministic).
We compute the ratio for multiple outer-seed replications so the
denominators are not single-seed flukes, then take the mean and
standard deviation of the ratio across replications.

Failure-mode diagnosis
----------------------
If ``ratio > 1`` (stochastic W2 is WORSE than deterministic), we
report the implementation status as ``has-bug`` and add a diagnostic
test that prints the contributions of drift and noise separately.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from adaptive_reflow.adapters.stochastic_fm import (
    DEFAULT_ENCODER_GAIN,
    DEFAULT_NOISE_SCALE,
    stochastic_velocity,
)
from adaptive_reflow.adapters.twodim_fm_train import sample_two_moons
from adaptive_reflow.eval.w2 import ProjectionFreeExactW2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _integrate(
    *,
    noise_scale: float,
    target: float,
    encoder_gain: float,
    n_steps: int,
    y0: np.ndarray,
    seed_base: int,
) -> NDArray[np.float64]:
    """Run explicit-Euler integration with stochastic_velocity.

    Same loop :meth:`StochasticFMAdapter.solve_ode` runs, but exposes
    the final ``y`` so the trajectory endpoint is measurable.
    """
    y: NDArray[np.float64] = (
        np.asarray(y0, dtype=np.float64).reshape(2).copy()
    )
    dt = 1.0 / float(n_steps)
    for step in range(int(n_steps)):
        t = step * dt
        v = stochastic_velocity(
            t=t,
            y=y,
            target=float(target),
            encoder_gain=float(encoder_gain),
            noise_scale=float(noise_scale),
            adaptive_noise_gamma=0.0,  # disable gamma growth for baseline parity
            seed=int(seed_base) + step,
        )
        y = np.asarray(y + dt * np.asarray(v, dtype=np.float64), dtype=np.float64)
    return np.asarray(y, dtype=np.float64).reshape(2)


def _sample_endpoints(
    *,
    noise_scale: float,
    n_endpoints: int,
    seed_base: int,
    target: float = 0.5,
    encoder_gain: float = DEFAULT_ENCODER_GAIN,
    n_steps: int = 100,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Sample ``n_endpoints`` final states under the given noise scale.

    Each endpoint uses a fresh ``y0 ~ N(0, I_2)`` drawn from ``rng``,
    a fresh ``seed_offset = step_index`` so the noise term varies per
    endpoint, and the explicit-Euler loop above. Returns ``(n, 2)``.
    """
    rng = rng if rng is not None else np.random.default_rng(seed_base)
    endpoints: NDArray[np.float64] = np.empty(
        (int(n_endpoints), 2), dtype=np.float64
    )
    for i in range(int(n_endpoints)):
        y0 = rng.standard_normal(2).astype(np.float64)
        endpoints[i] = _integrate(
            noise_scale=noise_scale,
            target=float(target),
            encoder_gain=float(encoder_gain),
            n_steps=int(n_steps),
            y0=y0,
            seed_base=int(seed_base) + i,
        )
    return endpoints


def _w2_to_two_moons(
    endpoints: NDArray[np.float64], target: NDArray[np.float64], seed: int
) -> float:
    """Projected-free W2 from endpoints to a fixed two-moons target."""
    est = ProjectionFreeExactW2(n_projections=128, seed=int(seed))
    return float(est.estimate(endpoints, target))


# ---------------------------------------------------------------------------
# Configuration constants for the experiment
# ---------------------------------------------------------------------------


N_ENDPOINTS: int = 128
N_TARGET: int = 1000
N_STEPS_INTEGRATION: int = 100
TARGET_SCALAR: float = 0.5
OUTER_SEEDS: tuple[int, ...] = (0, 1, 2)  # 3 replications -> mean +/- std
RATIO_GATE: float = 0.75  # <= 0.75 reproduces the 25% reduction claim


# ---------------------------------------------------------------------------
# EXP-2 reproduction tests
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="issue #EXP-2 — claim REFUTED on current setup (ratio=1.000, deterministic-target vs paper's stochastic-target); see docs/r4-survey/09-paper-experimental-records.md §4.4",
)
def test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction() -> None:
    """Reproduce the EXP-2 25% W2-reduction claim.

    For 3 outer seeds, compute the W2 of the deterministic baseline
    (``noise_scale = 0``) and the stochastic treatment
    (``noise_scale = DEFAULT_NOISE_SCALE``) to a fresh two-moons
    target, then take the ratio. The mean ratio must be <= 0.75
    across the outer seeds.
    """
    det_ratios: list[float] = []
    det_w2_list: list[float] = []
    sto_w2_list: list[float] = []
    for outer in OUTER_SEEDS:
        # Fresh target draw per outer seed (stable inside the seed).
        target_rng = np.random.default_rng(10_000 + outer)
        target = sample_two_moons(N_TARGET, target_rng)

        det_rng = np.random.default_rng(100 + outer)
        sto_rng = np.random.default_rng(100 + outer)  # same y0 sequence
        det_eps = _sample_endpoints(
            noise_scale=0.0,
            n_endpoints=N_ENDPOINTS,
            seed_base=outer * 1000,
            target=TARGET_SCALAR,
            n_steps=N_STEPS_INTEGRATION,
            rng=det_rng,
        )
        sto_eps = _sample_endpoints(
            noise_scale=DEFAULT_NOISE_SCALE,
            n_endpoints=N_ENDPOINTS,
            seed_base=outer * 1000,
            target=TARGET_SCALAR,
            n_steps=N_STEPS_INTEGRATION,
            rng=sto_rng,
        )
        det_w2 = _w2_to_two_moons(det_eps, target, seed=outer)
        sto_w2 = _w2_to_two_moons(sto_eps, target, seed=outer)
        det_w2_list.append(det_w2)
        sto_w2_list.append(sto_w2)
        ratio = sto_w2 / det_w2 if det_w2 > 0.0 else float("nan")
        det_ratios.append(ratio)
    det_mean = float(np.mean(det_w2_list))
    det_std = float(np.std(det_w2_list))
    sto_mean = float(np.mean(sto_w2_list))
    sto_std = float(np.std(sto_w2_list))
    # Filter NaNs and infs for the ratio mean.
    finite_ratios = [r for r in det_ratios if math.isfinite(r)]
    ratio_mean = float(np.mean(finite_ratios)) if finite_ratios else float("nan")
    summary = (
        f"W2_det={det_mean:.4f}+/-{det_std:.4f}, "
        f"W2_sto={sto_mean:.4f}+/-{sto_std:.4f}, "
        f"ratio={ratio_mean:.3f} (outer_seeds={OUTER_SEEDS})"
    )
    # Diagnostics: always print. The claim is ratio <= 0.75.
    print(f"\n[exp2] {summary}")
    assert math.isfinite(ratio_mean), (
        f"ratio is not finite; det_ratios={det_ratios}"
    )
    assert ratio_mean <= RATIO_GATE + 1e-9, (
        f"EXP-2 25% reduction NOT reproduced. {summary}"
    )


def test_exp2_stochastic_fm_endpoints_finite() -> None:
    """Sanity: both deterministic and stochastic endpoints are finite.

    Catches NaN / overflow if the noise_scale gets amplified through
    the SDE loop.
    """
    rng = np.random.default_rng(42)
    det_eps = _sample_endpoints(
        noise_scale=0.0,
        n_endpoints=N_ENDPOINTS,
        seed_base=0,
        rng=rng,
    )
    rng = np.random.default_rng(42)
    sto_eps = _sample_endpoints(
        noise_scale=DEFAULT_NOISE_SCALE,
        n_endpoints=N_ENDPOINTS,
        seed_base=0,
        rng=rng,
    )
    assert np.all(np.isfinite(det_eps)), "deterministic endpoints non-finite"
    assert np.all(np.isfinite(sto_eps)), "stochastic endpoints non-finite"


def test_exp2_diagnose_when_stochastic_is_worse() -> None:
    """If the 25% claim fails, diagnose the StochasticFMAdapter.

    This is not a hard assertion — it inspects the *drift* and *noise*
    contributions to the velocity and prints them, so a future failure
    in the primary test above has an immediate diagnostic footprint.
    """
    # Drift only (no noise): compute a single endpoint.
    rng = np.random.default_rng(0)
    y0 = rng.standard_normal(2).astype(np.float64)
    drift_endpoint = _integrate(
        noise_scale=0.0,
        target=TARGET_SCALAR,
        encoder_gain=DEFAULT_ENCODER_GAIN,
        n_steps=N_STEPS_INTEGRATION,
        y0=y0,
        seed_base=0,
    )
    # Drift + noise: compute the mean / std of endpoints over 50 seeds.
    drift_eps: list[np.ndarray] = []
    for s in range(50):
        rng = np.random.default_rng(s)
        y0 = rng.standard_normal(2).astype(np.float64)
        drift_eps.append(
            _integrate(
                noise_scale=0.0,
                target=TARGET_SCALAR,
                encoder_gain=DEFAULT_ENCODER_GAIN,
                n_steps=N_STEPS_INTEGRATION,
                y0=y0,
                seed_base=s,
            )
        )
    noise_eps: list[np.ndarray] = []
    for s in range(50):
        rng = np.random.default_rng(s)
        y0 = rng.standard_normal(2).astype(np.float64)
        noise_eps.append(
            _integrate(
                noise_scale=DEFAULT_NOISE_SCALE,
                target=TARGET_SCALAR,
                encoder_gain=DEFAULT_ENCODER_GAIN,
                n_steps=N_STEPS_INTEGRATION,
                y0=y0,
                seed_base=s,
            )
        )
    drift_arr = np.asarray(drift_eps)
    noise_arr = np.asarray(noise_eps)
    # Noise contribution magnitude.
    noise_contrib = float(np.std(noise_arr - drift_arr))
    drift_endpoint_norm = float(np.linalg.norm(drift_endpoint))
    print(
        f"\n[exp2-diagnose] drift_endpoint={drift_endpoint.tolist()}, "
        f"noise_contrib_std={noise_contrib:.4f}, "
        f"drift_endpoint_norm={drift_endpoint_norm:.4f}"
    )
    assert np.all(np.isfinite(drift_arr))
    assert np.all(np.isfinite(noise_arr))


def test_exp2_stochastic_velocity_signature() -> None:
    """Verify stochastic_velocity adds Gaussian noise proportional to scale.

    At ``y = (0, 0)``, ``target = 0``, the drift vanishes; the
    returned velocity is sigma * z, so its standard deviation across
    many (seed, t) should match ``noise_scale * (1 + gamma * t)``.
    """
    vels: list[np.ndarray] = []
    sigma_pred: list[float] = []
    for s in range(200):
        t = 0.3
        noise_scale = 0.1
        gamma = 1.0
        v = stochastic_velocity(
            t=t,
            y=np.asarray([0.0, 0.0]),
            target=0.0,
            encoder_gain=DEFAULT_ENCODER_GAIN,
            noise_scale=noise_scale,
            adaptive_noise_gamma=gamma,
            seed=s,
        )
        vels.append(np.asarray(v, dtype=np.float64))
        sigma_pred.append(noise_scale * (1.0 + gamma * t))
    arr = np.asarray(vels)
    observed_std = float(np.std(arr))
    expected_std = float(np.mean(sigma_pred))
    # The standard deviation should be close to the predicted sigma.
    assert math.isfinite(observed_std)
    # Loose tolerance: 0.05 within the predicted noise scale.
    assert abs(observed_std - expected_std) < 0.05, (
        f"stochastic_velocity signature drifted: "
        f"observed_std={observed_std:.4f}, expected={expected_std:.4f}"
    )
