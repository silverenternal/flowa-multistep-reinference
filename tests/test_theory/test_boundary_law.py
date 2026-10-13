"""CPU unit tests for the GAP-24 restart-blend boundary law.

The law is the closed form of Theorem 5's Eq. 7 improvement condition for
independent isotropic Gaussian residuals:

    the blend improves  <=>  q < sqrt((1 + m) / (1 - m)),   q = sigma_Y / sigma_X

These tests pin the closed-form helpers and check that ``blend_identity_terms``
reproduces the boundary on sampled Gaussian residuals. NumPy-only.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.theory.reinference_diagnostic import (
    blend_identity_terms,
    critical_memory,
    critical_restart_ratio,
)


def test_critical_helpers_are_inverses() -> None:
    for m in (0.1, 0.3, 0.5, 0.7, 0.9, 0.99):
        q = critical_restart_ratio(m)
        assert critical_memory(q) == pytest.approx(m, abs=1e-12)


def test_critical_ratio_monotone_and_limits() -> None:
    assert critical_restart_ratio(0.0) == pytest.approx(1.0)
    vals = [critical_restart_ratio(m) for m in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert vals == sorted(vals)  # strictly increasing in m
    assert critical_restart_ratio(0.5) == pytest.approx(math.sqrt(3.0))


def test_critical_memory_sign() -> None:
    assert critical_memory(1.0) == pytest.approx(0.0)
    assert critical_memory(0.5) < 0.0  # q < 1 always improves
    assert critical_memory(1.5) == pytest.approx(0.3846153846153846)


@pytest.mark.parametrize("m", [0.3, 0.5, 0.7])
def test_boundary_matches_gaussian_identity(m: float) -> None:
    rng = np.random.default_rng(0)
    n, d = 20000, 8
    z = rng.standard_normal((n, d))
    q_crit = critical_restart_ratio(m)
    for q in (0.5, 0.8, 1.0, 1.2, 1.6, 2.0, 3.0):
        if abs(q - q_crit) <= 0.02 * q_crit:
            continue  # sign is undefined exactly on the boundary
        X = z + rng.standard_normal((n, d))
        Y = z + q * rng.standard_normal((n, d))
        rep = blend_identity_terms(X, Y, z, m=m)
        assert rep.condition_holds == (q < q_crit)
        assert rep.prediction_matches


def test_q_at_or_below_one_always_improves() -> None:
    rng = np.random.default_rng(1)
    n, d = 20000, 8
    z = rng.standard_normal((n, d))
    for m in (0.2, 0.5, 0.8):
        X = z + rng.standard_normal((n, d))
        Y = z + 0.5 * rng.standard_normal((n, d))  # q = 0.5 < 1
        rep = blend_identity_terms(X, Y, z, m=m)
        assert rep.condition_holds
        assert rep.measured_blend_better


def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError):
        critical_restart_ratio(1.0)
    with pytest.raises(ValueError):
        critical_restart_ratio(-0.1)
    with pytest.raises(ValueError):
        critical_memory(-1.0)
