"""Wave 33 Phase 2 Agent E: regression tests for HIGH-confidence Fix C.

Gap C: LineageFlow ``family_validity`` decision metric saturates at
1.0 (per Wave 19 P1A2 §6.1), so the framework-vs-baseline gap is
**non-degenerate by construction** (always zero). The fix replaces
the saturated binary metric with a **continuous** metric: per-position
mean entropy of the endpoint distribution.

The tests below verify:

* ``test_per_position_entropy_is_continuous``: the metric is
  continuous (varies smoothly with the input) and never saturates
  at 1.0 like ``family_validity`` does.
* ``test_per_position_entropy_maximum_for_uniform``: the metric is
  bounded above by ``log(K)`` (the maximum entropy of a uniform
  distribution over the ``K`` amino-acid dimension).
* ``test_per_position_entropy_minimum_for_concentrated``: a delta
  spike at a single amino acid gives ~0 entropy (concentrated).
* ``test_per_position_entropy_discriminates``: two different
  endpoint distributions yield different entropy values (no
  saturation).
* ``test_per_position_entropy_empty_input``: degenerate inputs
  return ``nan`` without crashing.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from tools.run_controlled_audit import (
    _family_validity,
    _per_position_entropy,
)


def test_per_position_entropy_is_continuous() -> None:
    """The entropy metric is continuous in the input (no saturation)."""
    rng = np.random.default_rng(0)
    # ``family_validity`` saturates at 1.0 for both distributions
    # below (the Wave 19 P1A2 finding). The new metric must still
    # distinguish them. We use one concentrated distribution and one
    # spread distribution so the entropy gap is clearly positive.
    # Concentrated: low variance + bias on amino acid 7.
    concentrated = rng.standard_normal((16, 64, 33)).astype(np.float64) * 0.1
    concentrated[..., 7] += 5.0  # bias toward amino acid 7
    # Spread: higher variance → softer distribution.
    spread = rng.standard_normal((16, 64, 33)).astype(np.float64) * 1.0
    entropy_concentrated = _per_position_entropy(concentrated)
    entropy_spread = _per_position_entropy(spread)
    # ``family_validity`` would saturate at 1.0 for BOTH inputs;
    # ``_per_position_entropy`` distinguishes them.
    assert math.isfinite(entropy_concentrated)
    assert math.isfinite(entropy_spread)
    # Concentrated → lower entropy; spread → higher entropy.
    assert entropy_concentrated < entropy_spread


def test_per_position_entropy_maximum_for_uniform() -> None:
    """The metric is bounded above by ``log(K)`` (uniform distribution)."""
    K = 33
    # All-zeros endpoints → uniform distribution after softmax → max entropy.
    endpoints = np.zeros((8, 16, K), dtype=np.float64)
    entropy = _per_position_entropy(endpoints)
    assert math.isfinite(entropy)
    # Each position has uniform distribution over K amino acids.
    # Maximum entropy per position = log(K). Mean over positions = log(K).
    assert entropy == pytest.approx(math.log(K), abs=1e-3)


def test_per_position_entropy_minimum_for_concentrated() -> None:
    """A delta spike at one amino acid gives ~0 entropy (concentrated)."""
    K = 33
    L = 16
    N = 8
    endpoints = np.full((N, L, K), -100.0, dtype=np.float64)
    # Set amino acid 5 to a very high value → concentrated at index 5.
    endpoints[..., 5] = 100.0
    entropy = _per_position_entropy(endpoints)
    assert math.isfinite(entropy)
    # Concentration at a single amino acid → entropy ≈ 0.
    assert entropy < 1e-3


def test_per_position_entropy_discriminates() -> None:
    """Two different endpoint distributions yield different entropy values.

    This is the regression test for the framework-vs-baseline gap:
    ``family_validity`` cannot distinguish these; the new metric can.
    """
    rng = np.random.default_rng(42)
    # Concentrated distribution (low entropy); keep within [-10, 10].
    concentrated = rng.standard_normal((8, 32, 33)).astype(np.float64) * 0.05
    concentrated[..., 7] += 5.0  # bias toward amino acid 7
    # Spread distribution (high entropy); keep within [-10, 10].
    spread = rng.standard_normal((8, 32, 33)).astype(np.float64) * 0.5
    e_concentrated = _per_position_entropy(concentrated)
    e_spread = _per_position_entropy(spread)
    assert e_concentrated < e_spread
    # And ``family_validity`` saturates at 1.0 for both (the original
    # Wave 19 P1A2 finding).
    assert _family_validity(concentrated) == pytest.approx(1.0, abs=1e-9)
    assert _family_validity(spread) == pytest.approx(1.0, abs=1e-9)


def test_per_position_entropy_empty_input() -> None:
    """Empty or degenerate inputs return ``nan`` without crashing."""
    # Empty array.
    empty = np.zeros((0, 16, 33), dtype=np.float64)
    assert math.isnan(_per_position_entropy(empty))
    # Single sample → no batch to average over.
    single = np.zeros((1, 16, 33), dtype=np.float64)
    assert math.isnan(_per_position_entropy(single))


def test_per_position_entropy_bounds() -> None:
    """The metric is bounded in ``[0, log(K)]`` for any input."""
    K = 33
    rng = np.random.default_rng(123)
    for _ in range(20):
        endpoints = rng.standard_normal((8, 32, K)).astype(np.float64) * (
            rng.uniform(0.01, 10.0)
        )
        entropy = _per_position_entropy(endpoints)
        assert 0.0 <= entropy <= math.log(K) + 1e-6
