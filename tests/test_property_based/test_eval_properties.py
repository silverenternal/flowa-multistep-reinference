"""Property-based tests for :mod:`adaptive_reflow.eval`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :func:`eval.w2.pairwise_squared_distances` — symmetry
  ``d(x, y) == d(y, x)``; non-negativity; ``d(x, x) == 0``.
* :class:`eval.w2.ModeCentreMSEW2` — ``W2(X, X) == 0`` (note: this is
  NOT a symmetric Wasserstein distance — see the docstring;
  ``W2(X, Y) != W2(Y, X)`` in general).
* :func:`eval.lipschitz_diagnostic.bounded_lipschitz_distance_2d` —
  triangle inequality on sampled inputs; symmetry.

Seed policy (Research 4 mitigation): these are deterministic algorithms
(sampled W2 / BL distances); Hypothesis varies only the input tuples.
"""

from __future__ import annotations

import math

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.eval.lipschitz_diagnostic import (
    bounded_lipschitz_distance_2d,
)
from adaptive_reflow.eval.w2 import (
    ModeCentreMSEW2,
    _pairwise_distances,
)


_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


# 1-D points for the pairwise-distance helpers (ModeCentreMSEW2
# accepts (n, d) arrays; we use d=1 for the per-element tests).
_POINTS_1D = st.lists(
    st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    min_size=2,
    max_size=8,
).map(lambda xs: np.asarray(xs, dtype=np.float64).reshape(-1, 1))


# 2-D points for the bounded_lipschitz_distance_2d helper.
@st.composite
def _planar_points(draw, *, min_size: int = 2, max_size: int = 8) -> np.ndarray:
    xs = draw(
        st.lists(
            st.floats(min_value=-5.0, max_value=5.0, allow_nan=False),
            min_size=min_size,
            max_size=max_size,
        )
    )
    ys = draw(
        st.lists(
            st.floats(min_value=-5.0, max_value=5.0, allow_nan=False),
            min_size=min_size,
            max_size=max_size,
        )
    )
    n = min(len(xs), len(ys))
    return np.stack(
        [np.asarray(xs[:n], dtype=np.float64), np.asarray(ys[:n], dtype=np.float64)],
        axis=-1,
    )


# ---------------------------------------------------------------------------
# pairwise_distances: symmetry, non-negativity, reflexivity.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(points=_POINTS_1D)
def test_pairwise_distances_symmetry(points: np.ndarray) -> None:
    """``D[i, j] == D[j, i]`` for the pairwise-distance matrix."""
    D = _pairwise_distances(points)
    n = int(D.shape[0])
    for i in range(n):
        for j in range(n):
            assert math.isclose(D[i, j], D[j, i], abs_tol=1e-12)


@_PROPERTY_SETTINGS
@given(points=_POINTS_1D)
def test_pairwise_distances_nonnegative_and_zero_diagonal(points: np.ndarray) -> None:
    """D[i, j] >= 0 and D[i, i] == 0 for every i, j."""
    D = _pairwise_distances(points)
    n = int(D.shape[0])
    for i in range(n):
        assert math.isclose(D[i, i], 0.0, abs_tol=1e-12)
        for j in range(n):
            assert D[i, j] >= -1e-12


# ---------------------------------------------------------------------------
# ModeCentreMSEW2: identity W2(X, X) == 0.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(points=_POINTS_1D)
def test_mode_centre_mse_w2_self_distance_is_zero(points: np.ndarray) -> None:
    """``W2(X, X) == 0`` (ModeCentreMSEW2 evaluates the mean squared
    distance to the nearest reference point — every sample is itself a
    reference point at zero cost)."""
    estimator = ModeCentreMSEW2()
    out = estimator.estimate(points, points)
    assert math.isclose(out, 0.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# bounded_lipschitz_distance_2d: triangle inequality on sampled inputs.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    x=_planar_points(),
    y=_planar_points(),
    z=_planar_points(),
    bound=st.floats(min_value=0.5, max_value=4.0, allow_nan=False),
)
def test_bounded_lipschitz_triangle_inequality(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, bound: float
) -> None:
    """BL(X, Z) <= BL(X, Y) + BL(Y, Z) — sampled triangle inequality."""
    bl_xy = bounded_lipschitz_distance_2d(x, y, bound=bound)
    bl_yz = bounded_lipschitz_distance_2d(y, z, bound=bound)
    bl_xz = bounded_lipschitz_distance_2d(x, z, bound=bound)
    assert math.isfinite(bl_xy)
    assert math.isfinite(bl_yz)
    assert math.isfinite(bl_xz)
    assert bl_xy >= -1e-12
    assert bl_yz >= -1e-12
    assert bl_xz >= -1e-12
    # triangle inequality (with float-slop tolerance).
    assert bl_xz <= bl_xy + bl_yz + 1e-6 * (bl_xy + bl_yz + 1.0)


@_PROPERTY_SETTINGS
@given(
    x=_planar_points(),
    y=_planar_points(),
    bound=st.floats(min_value=0.5, max_value=4.0, allow_nan=False),
)
def test_bounded_lipschitz_symmetry(
    x: np.ndarray, y: np.ndarray, bound: float
) -> None:
    """``BL(X, Y) == BL(Y, X)`` — sampled symmetry."""
    bl_xy = bounded_lipschitz_distance_2d(x, y, bound=bound)
    bl_yx = bounded_lipschitz_distance_2d(y, x, bound=bound)
    assert math.isclose(bl_xy, bl_yx, abs_tol=1e-9)


@_PROPERTY_SETTINGS
@given(
    x=_planar_points(),
    bound=st.floats(min_value=0.5, max_value=4.0, allow_nan=False),
)
def test_bounded_lipschitz_self_distance_is_zero(
    x: np.ndarray, bound: float
) -> None:
    """``BL(X, X) == 0`` (every point is matched to itself at zero cost)."""
    bl = bounded_lipschitz_distance_2d(x, x, bound=bound)
    assert math.isclose(bl, 0.0, abs_tol=1e-9)