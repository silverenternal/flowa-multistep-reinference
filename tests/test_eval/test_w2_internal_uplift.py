"""Framework-INTERNAL W2 uplift: registry plug-in + variance target.

Complements ``test_w2_external_uplifts.py`` (which covers the estimator
surface itself) by asserting the two quantitative claims the *framework*
relies on:

* the projection-free estimator reduces the squared coefficient of
  variation by ``>= 50 %`` versus the legacy ``mode_centre_mse`` at
  ``n = 128``;
* it stays inside the per-call runtime budget so it can sit in the
  batched runner's per-round hot loop.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from adaptive_reflow.eval.w2 import (
    DEFAULT_W2_FAMILY,
    W2_REGISTRY,
    W2Family,
    build_w2_estimator,
    compute_w2,
)

MODE_CENTRES = np.asarray([[0.5, 0.0], [-0.5, 0.0]], dtype=np.float64)
N_ENDPOINTS = 128
N_SEEDS = 200


def _population(seed: int, n: int = N_ENDPOINTS) -> np.ndarray:
    """Return a two-mode endpoint population, deterministic in ``seed``."""
    rng = np.random.default_rng(seed)
    labels = rng.integers(0, MODE_CENTRES.shape[0], size=n)
    return MODE_CENTRES[labels] + rng.normal(0.0, 0.4, size=(n, 2))


def _squared_cv(values: list[float]) -> float:
    """Return ``(std / mean) ** 2`` — the scale-free variance."""
    arr = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(arr))
    assert mean > 0.0
    return float((float(np.std(arr)) / mean) ** 2)


# ---------------------------------------------------------------------------
# Registry / default preservation
# ---------------------------------------------------------------------------


def test_default_family_is_the_legacy_surrogate() -> None:
    """Opting out of the registry must change nothing."""
    assert DEFAULT_W2_FAMILY == W2Family.MODE_CENTRE_MSE


def test_registry_covers_every_declared_family() -> None:
    assert set(W2Family.all()) == set(W2_REGISTRY)


def test_compute_w2_default_matches_legacy_arithmetic() -> None:
    """``compute_w2`` with defaults reproduces mean-min-squared exactly."""
    pts = _population(0)
    diff = pts[:, None, :] - MODE_CENTRES[None, :, :]
    expected = float(np.min((diff * diff).sum(axis=-1), axis=1).mean())
    assert compute_w2(pts, MODE_CENTRES) == pytest.approx(expected, rel=1e-15)


def test_every_family_is_finite_and_non_negative() -> None:
    pts = _population(1)
    for family in W2Family.all():
        value = compute_w2(pts, MODE_CENTRES, family=family)
        assert np.isfinite(value), family
        assert value >= 0.0, family


def test_estimators_are_deterministic() -> None:
    """Same inputs -> bit-identical output (required for ledger rows)."""
    pts = _population(2)
    for family in W2Family.all():
        first = compute_w2(pts, MODE_CENTRES, family=family)
        second = compute_w2(pts, MODE_CENTRES, family=family)
        assert first == second, family


# ---------------------------------------------------------------------------
# Quantitative target: >= 50 % squared-CV reduction at n = 128
# ---------------------------------------------------------------------------


def test_projection_free_halves_squared_cv_vs_legacy() -> None:
    """P0 #3 target: squared coefficient of variation down by >= 50 %."""
    legacy = build_w2_estimator(W2Family.MODE_CENTRE_MSE)
    projection = build_w2_estimator(W2Family.PROJECTION_FREE, n_projections=128, seed=0)

    legacy_values: list[float] = []
    projection_values: list[float] = []
    for seed in range(N_SEEDS):
        pts = _population(seed)
        legacy_values.append(legacy.estimate(pts, MODE_CENTRES))
        projection_values.append(projection.estimate(pts, MODE_CENTRES))

    legacy_cv2 = _squared_cv(legacy_values)
    projection_cv2 = _squared_cv(projection_values)
    reduction = 1.0 - projection_cv2 / legacy_cv2
    assert reduction >= 0.50, (
        f"projection_free squared-CV reduction {reduction:.3f} "
        f"(legacy={legacy_cv2:.6f}, projection_free={projection_cv2:.6f}) "
        f"missed the >= 0.50 target"
    )


def test_projection_free_stays_inside_the_per_call_budget() -> None:
    """The estimator sits in the runner's per-round loop; keep it cheap."""
    estimator = build_w2_estimator(W2Family.PROJECTION_FREE, n_projections=128, seed=0)
    pts = _population(3)
    estimator.estimate(pts, MODE_CENTRES)  # warm up

    start = time.perf_counter()
    repeats = 20
    for _ in range(repeats):
        estimator.estimate(pts, MODE_CENTRES)
    per_call_ms = (time.perf_counter() - start) / repeats * 1000.0
    assert per_call_ms < 5.0, f"projection_free took {per_call_ms:.3f} ms/call"


def test_projection_free_is_mass_aware_unlike_the_legacy_statistic() -> None:
    """A population collapsed onto one centre must be penalised.

    The legacy nearest-centre statistic scores a fully-collapsed
    population at ``0`` — it never notices the missing mode. The
    projection-free estimator transports the surplus mass and so scores
    it strictly worse than a balanced population.
    """
    collapsed = np.repeat(MODE_CENTRES[:1], N_ENDPOINTS, axis=0)
    balanced = np.repeat(MODE_CENTRES, N_ENDPOINTS // 2, axis=0)

    legacy = build_w2_estimator(W2Family.MODE_CENTRE_MSE)
    assert legacy.estimate(collapsed, MODE_CENTRES) == pytest.approx(0.0, abs=1e-12)
    assert legacy.estimate(balanced, MODE_CENTRES) == pytest.approx(0.0, abs=1e-12)

    projection = build_w2_estimator(W2Family.PROJECTION_FREE, n_projections=128, seed=0)
    assert projection.estimate(collapsed, MODE_CENTRES) > projection.estimate(
        balanced, MODE_CENTRES
    )
