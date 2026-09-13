"""Smoke test suite for the LineageFlow glue composite layer (Wave 47).

Mirrors :mod:`tests.test_adapters.test_lineageflow`'s structure for the
dedicated pure-glue ``LineageFlowGlue`` class. The glue layer is a
**pure consumer** of :class:`LineageFlowAdapter`; the tests here use a
fake adapter that holds trajectory entries in a plain dict so the
glue can run without instantiating the heavy real adapter or its
sidecar venv.

5 tests; all CPU-runnable. Stdlib + numpy only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from adaptive_reflow.adapters.lineageflow_glue import (
    DEFAULT_COMPOSITE_WEIGHTS,
    LINEAGEFLOW_COMPOSITE_KEY,
    LINEAGEFLOW_VOCAB_SIZE,
    LineageFlowGlue,
)

# ---------------------------------------------------------------------------
# Helpers — fake adapter + fake trace (no torch, no real adapter)
# ---------------------------------------------------------------------------


@dataclass
class _FakeTrace:
    """Minimal duck-typed :class:`ODEIntegratorTrace` for tests."""

    native_state_digest: str
    steps: int = 50
    accept_rate: float = 1.0
    integrator_config_hash: str = "fake-hash"


@dataclass
class _FakeAdapter:
    """Fake adapter exposing ``_native_states`` as a plain dict.

    Mirrors the relevant slice of
    :class:`LineageFlowAdapter._native_states` — the glue only does
    ``adapter._native_states[trace.native_state_digest]`` and reads
    the ``"trajectory"`` entry. No Protocol methods are exercised
    by the glue.
    """

    _native_states: dict[str, dict[str, Any]] = field(default_factory=dict)


def _make_trajectory(theta_final: np.ndarray, *, n_steps: int = 5) -> np.ndarray:
    """Build a synthetic ``(N+1, L, K)`` trajectory whose final step is
    ``theta_final``. Intermediate steps are interpolated linearly from
    a uniform prior so the cache shape matches
    :class:`LineageFlowAdapter`'s native-state cache layout.
    """
    L, K = theta_final.shape
    prior = np.full((L, K), 1.0 / K, dtype=np.float64)
    traj = np.empty((n_steps + 1, L, K), dtype=np.float64)
    traj[0] = prior
    for i in range(1, n_steps + 1):
        alpha = i / n_steps
        traj[i] = (1.0 - alpha) * prior + alpha * theta_final
        # Re-normalise to keep the trajectory row-normalised (LineageFlow
        # invariant).
        traj[i] = traj[i] / np.maximum(traj[i].sum(axis=-1, keepdims=True), 1e-30)
    return traj


def _fake_adapter_with_endpoints(
    theta_b: np.ndarray, theta_f: np.ndarray
) -> tuple[_FakeAdapter, _FakeTrace, _FakeTrace]:
    """Build a fake adapter whose cache holds two trajectories.

    Returns ``(adapter, baseline_trace, framework_trace)``.
    """
    L, K = theta_b.shape
    assert theta_f.shape == (L, K)
    adapter = _FakeAdapter()
    b_traj = _make_trajectory(theta_b, n_steps=5)
    f_traj = _make_trajectory(theta_f, n_steps=5)
    adapter._native_states["digest-b"] = {"trajectory": b_traj}
    adapter._native_states["digest-f"] = {"trajectory": f_traj}
    return adapter, _FakeTrace("digest-b"), _FakeTrace("digest-f")


def _row_normalised(theta: np.ndarray) -> np.ndarray:
    """Row-normalise a ``(L, K)`` matrix along the trailing axis."""
    theta = np.asarray(theta, dtype=np.float64)
    return theta / np.maximum(theta.sum(axis=-1, keepdims=True), 1e-30)


def _uniform(L: int = 64, K: int = LINEAGEFLOW_VOCAB_SIZE) -> np.ndarray:
    return np.full((L, K), 1.0 / K, dtype=np.float64)


def _delta(L: int, k_star: int, K: int = LINEAGEFLOW_VOCAB_SIZE) -> np.ndarray:
    """A row-normalised categorical concentrated on ``k_star``."""
    delta = np.zeros((L, K), dtype=np.float64)
    delta[:, k_star] = 1.0
    return delta


# ---------------------------------------------------------------------------
# Test 1 — imports + __all__
# ---------------------------------------------------------------------------


def test_glue_imports_and_all():
    """``LineageFlowGlue`` + 3 module-level constants are importable."""
    assert LineageFlowGlue is not None
    assert LINEAGEFLOW_COMPOSITE_KEY == "lineageflow_composite"
    assert LINEAGEFLOW_VOCAB_SIZE == 33
    assert sum(DEFAULT_COMPOSITE_WEIGHTS) == pytest.approx(1.0)
    # Check all 3 weights are non-negative.
    for w in DEFAULT_COMPOSITE_WEIGHTS:
        assert w >= 0.0


# ---------------------------------------------------------------------------
# Test 2 — uniform-to-spike: composite must be > 0
# ---------------------------------------------------------------------------


def test_glue_compute_composite_uniform_to_spike():
    """Baseline uniform; framework sharp on a residue → composite > 0."""
    L = 64
    K = LINEAGEFLOW_VOCAB_SIZE
    # Baseline: uniform. Framework: half positions uniform, half a
    # delta-spike on residue 5. Net: framework is sharper on average
    # → entropy reduction positive; max-prob delta positive; some
    # argmax turnover but not zero.
    theta_b = _uniform(L, K)
    theta_f = _row_normalised(
        np.vstack([_uniform(L // 2, K), _delta(L // 2, 5, K)])
    )
    adapter, b_trace, f_trace = _fake_adapter_with_endpoints(theta_b, theta_f)
    glue = LineageFlowGlue(adapter=adapter)

    result = glue.compute_composite(b_trace, f_trace, seed=42, nfe=50)

    assert -1.0 <= result["composite"] <= 1.0
    # Framework is sharper on average → composite should be positive.
    assert result["composite"] > 0.0, (
        f"framework sharper than baseline → expected composite > 0, "
        f"got {result['composite']}"
    )
    # phi1 (entropy reduction normalised) should be positive: framework
    # entropy is lower than baseline.
    assert result["phi1_entropy_reduction_normalised"] > 0.0
    # phi2 (max-prob delta) should be positive: framework has higher
    # max-prob on the spike positions.
    assert result["phi2_max_prob_delta"] > 0.0
    # Audit fields echoed.
    assert result["seed"] == 42
    assert result["nfe"] == 50
    assert result["K"] == K
    assert result["weights"] == list(DEFAULT_COMPOSITE_WEIGHTS)


# ---------------------------------------------------------------------------
# Test 3 — identical endpoints → composite == 0
# ---------------------------------------------------------------------------


def test_glue_compute_composite_identical_endpoints():
    """Same theta on both arms → phi1=phi2=0; phi3=-1 by formula design.

    Per Wave 47 Agent C §3.2, the ``phi3_argmax_turnover_signed`` formula
    is ``2 * mean(argmax_f != argmax_b) - 1``, so ``turnover = 0`` maps
    to ``phi3 = -1`` (the design doc notes this "can't happen in practice
    because both arms are non-degenerate"). With identical endpoints:
    turnover = 0 exactly, so ``phi3 = -1``, ``phi1 = phi2 = 0``, and
    composite = ``0.25 * -1 = -0.25``. This is the synthetic-mode
    collapse reading from Agent C §5.1.
    """
    L = 32
    K = LINEAGEFLOW_VOCAB_SIZE
    # Use a non-uniform but identical endpoint on both arms.
    rng = np.random.default_rng(0)
    raw = rng.uniform(0.0, 1.0, size=(L, K))
    theta = _row_normalised(raw)

    adapter, b_trace, f_trace = _fake_adapter_with_endpoints(theta, theta)
    glue = LineageFlowGlue(adapter=adapter)

    result = glue.compute_composite(b_trace, f_trace)

    # phi1 and phi2 are zero because the two thetas are identical.
    assert result["phi1_entropy_reduction_normalised"] == pytest.approx(0.0, abs=1e-12)
    assert result["phi2_max_prob_delta"] == pytest.approx(0.0, abs=1e-12)
    # phi3 = 2 * 0 - 1 = -1 by formula design (no turnover = -1).
    assert result["phi3_argmax_turnover_signed"] == pytest.approx(-1.0, abs=1e-12)
    # composite = 0.40 * 0 + 0.35 * 0 + 0.25 * -1 = -0.25.
    assert result["composite"] == pytest.approx(-0.25, abs=1e-12)


# ---------------------------------------------------------------------------
# Test 4 — composite bounded in [-1, +1] across 50 random pairs
# ---------------------------------------------------------------------------


def test_glue_compute_composite_bounded():
    """50 random ``(L, K)`` endpoint pairs; composite ∈ [-1, +1]."""
    K = LINEAGEFLOW_VOCAB_SIZE
    rng = np.random.default_rng(2026)
    for _ in range(50):
        L = int(rng.integers(8, 256))
        # Random row-normalised baselines + frameworks.
        theta_b = _row_normalised(rng.uniform(0.0, 1.0, size=(L, K)))
        theta_f = _row_normalised(rng.uniform(0.0, 1.0, size=(L, K)))
        adapter, b_trace, f_trace = _fake_adapter_with_endpoints(theta_b, theta_f)
        glue = LineageFlowGlue(adapter=adapter)
        result = glue.compute_composite(b_trace, f_trace)
        assert -1.0 <= result["composite"] <= 1.0, (
            f"composite {result['composite']} out of [-1, 1] "
            f"for L={L}"
        )
        assert -1.0 <= result["phi1_entropy_reduction_normalised"] <= 1.0
        assert -1.0 <= result["phi2_max_prob_delta"] <= 1.0
        assert -1.0 <= result["phi3_argmax_turnover_signed"] <= 1.0


# ---------------------------------------------------------------------------
# Test 5 — weights validation
# ---------------------------------------------------------------------------


def test_glue_compute_composite_weights_validation():
    """Rejects weights that don't sum to 1.0 (negative, too many, wrong sum)."""
    L, K = 16, LINEAGEFLOW_VOCAB_SIZE
    theta_b = _uniform(L, K)
    theta_f = _uniform(L, K)
    adapter, b_trace, f_trace = _fake_adapter_with_endpoints(theta_b, theta_f)
    glue = LineageFlowGlue(adapter=adapter)

    # Sum > 1.0
    with pytest.raises(ValueError, match="sum to 1.0"):
        glue.compute_composite(b_trace, f_trace, weights=(0.5, 0.3, 0.3))
    # Sum < 1.0
    with pytest.raises(ValueError, match="sum to 1.0"):
        glue.compute_composite(b_trace, f_trace, weights=(0.2, 0.2, 0.2))
    # Negative weight
    with pytest.raises(ValueError, match="non-negative"):
        glue.compute_composite(b_trace, f_trace, weights=(0.6, 0.5, -0.1))
    # Wrong length
    with pytest.raises(ValueError, match="length 3"):
        glue.compute_composite(b_trace, f_trace, weights=(0.5, 0.5))
    # Custom valid weights succeed.
    result = glue.compute_composite(
        b_trace, f_trace, weights=(0.5, 0.25, 0.25)
    )
    assert result["weights"] == [0.5, 0.25, 0.25]
