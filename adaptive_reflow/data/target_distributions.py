"""Canonical two-dimensional targets shared by Flow Matching experiments.

The arrays in this module are intentionally the single source of truth for
the 2D adapter, its evaluator, and experiment tools.  Samplers accept an
explicit NumPy generator so experiment replay remains deterministic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

Array: TypeAlias = NDArray[np.float64]
Sampler: TypeAlias = Callable[[int, np.random.Generator], Array]

TWO_MOONS_NOISE: float = 0.08
TWO_MOONS_SAMPLER_CENTERS: Array = np.asarray([[0.0, 0.0], [1.0, -0.5]], dtype=np.float64)
TWO_MOONS_MODE_CENTERS: Array = np.asarray([[0.0, 1.0], [1.0, -0.5]], dtype=np.float64)
TWO_MOONS_POSTERIOR_SHEET: tuple[float, float] = (0.5, 0.0)
TWO_MOONS_POSTERIOR_CELLS: tuple[tuple[float, float], ...] = ((-0.5, 0.0),)

EIGHT_GAUSSIANS_SAMPLER_RADIUS: float = 2.0
EIGHT_GAUSSIANS_SAMPLER_STDDEV: float = 0.15
_EIGHT_GAUSSIANS_ANGLES: Array = np.arange(8, dtype=np.float64) * (np.pi / 4.0)
EIGHT_GAUSSIANS_SAMPLER_CENTERS: Array = EIGHT_GAUSSIANS_SAMPLER_RADIUS * np.stack(
    [np.cos(_EIGHT_GAUSSIANS_ANGLES), np.sin(_EIGHT_GAUSSIANS_ANGLES)], axis=1
)
EIGHT_GAUSSIANS_MODE_CENTERS: Array = EIGHT_GAUSSIANS_SAMPLER_CENTERS
EIGHT_GAUSSIANS_POSTERIOR_RADIUS: float = float(np.sqrt(2.0))
_EIGHT_GAUSSIANS_POSTERIOR_ANGLES: Array = np.arange(8, dtype=np.float64) * (np.pi / 4.0)
_EIGHT_GAUSSIANS_POSTERIOR_CENTERS: Array = EIGHT_GAUSSIANS_POSTERIOR_RADIUS * np.stack(
    [np.cos(_EIGHT_GAUSSIANS_POSTERIOR_ANGLES), np.sin(_EIGHT_GAUSSIANS_POSTERIOR_ANGLES)],
    axis=1,
)
EIGHT_GAUSSIANS_POSTERIOR_SHEET: tuple[float, float] = (
    EIGHT_GAUSSIANS_POSTERIOR_RADIUS,
    0.0,
)
EIGHT_GAUSSIANS_POSTERIOR_CELLS: tuple[tuple[float, float], ...] = tuple(
    (float(x), float(y)) for x, y in _EIGHT_GAUSSIANS_POSTERIOR_CENTERS[1:]
)

SWISS_ROLL_NOISE: float = 0.08
_SWISS_ROLL_T: Array = np.linspace(1.5 * np.pi, 4.5 * np.pi, 6, dtype=np.float64)
SWISS_ROLL_SAMPLER_CENTERS: Array = np.stack(
    [
        _SWISS_ROLL_T * np.cos(_SWISS_ROLL_T) / (2.0 * np.pi),
        _SWISS_ROLL_T * np.sin(_SWISS_ROLL_T) / (2.0 * np.pi),
    ],
    axis=1,
)
SWISS_ROLL_MODE_CENTERS: Array = SWISS_ROLL_SAMPLER_CENTERS

PINWHEEL_NOISE: float = 0.12
_PINWHEEL_ANGLES: Array = np.arange(5, dtype=np.float64) * (2.0 * np.pi / 5.0)
PINWHEEL_SAMPLER_CENTERS: Array = 2.0 * np.stack(
    [np.cos(_PINWHEEL_ANGLES), np.sin(_PINWHEEL_ANGLES)], axis=1
)
PINWHEEL_MODE_CENTERS: Array = PINWHEEL_SAMPLER_CENTERS

CHECKERBOARD_NOISE: float = 0.12
CHECKERBOARD_SAMPLER_CENTERS: Array = np.asarray(
    [[-1.0, -1.0], [-1.0, 1.0], [1.0, -1.0], [1.0, 1.0]], dtype=np.float64
)
CHECKERBOARD_MODE_CENTERS: Array = CHECKERBOARD_SAMPLER_CENTERS

GAUSSIAN_GRID_NOISE: float = 0.12
_GAUSSIAN_GRID_AXIS: Array = np.linspace(-2.0, 2.0, 5, dtype=np.float64)
GAUSSIAN_GRID_SAMPLER_CENTERS: Array = np.asarray(
    [(float(x), float(y)) for x in _GAUSSIAN_GRID_AXIS for y in _GAUSSIAN_GRID_AXIS],
    dtype=np.float64,
)
GAUSSIAN_GRID_MODE_CENTERS: Array = GAUSSIAN_GRID_SAMPLER_CENTERS


def _validate_n(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("n_must_be_positive")
    return n


def sample_two_moons(n: int, rng: np.random.Generator) -> Array:
    """Sample the canonical two-moons target."""
    count = _validate_n(n)
    n_a = count // 2
    n_b = count - n_a
    theta_a = rng.uniform(0.0, np.pi, size=n_a)
    theta_b = rng.uniform(0.0, np.pi, size=n_b)
    moon_a = np.stack([np.cos(theta_a), np.sin(theta_a)], axis=1)
    moon_b = np.stack([1.0 - np.cos(theta_b), -np.sin(theta_b) - 0.5], axis=1)
    points = np.concatenate([moon_a, moon_b], axis=0)
    return np.asarray(
        points + TWO_MOONS_NOISE * rng.standard_normal(points.shape), dtype=np.float64
    )


def _sample_centred_mixture(
    n: int, rng: np.random.Generator, centers: Array, noise: float
) -> Array:
    count = _validate_n(n)
    indices = rng.integers(0, centers.shape[0], size=count)
    return np.asarray(centers[indices] + noise * rng.standard_normal((count, 2)), dtype=np.float64)


def sample_eight_gaussians(n: int, rng: np.random.Generator) -> Array:
    """Sample eight isotropic Gaussians arranged on the canonical radius-2 ring."""
    return _sample_centred_mixture(
        n, rng, EIGHT_GAUSSIANS_SAMPLER_CENTERS, EIGHT_GAUSSIANS_SAMPLER_STDDEV
    )


def sample_swiss_roll(n: int, rng: np.random.Generator) -> Array:
    """Sample a two-dimensional Swiss-roll spiral with isotropic perturbation."""
    count = _validate_n(n)
    angle = rng.uniform(1.5 * np.pi, 4.5 * np.pi, size=count)
    radius = angle / (2.0 * np.pi)
    points = np.stack([radius * np.cos(angle), radius * np.sin(angle)], axis=1)
    return np.asarray(
        points + SWISS_ROLL_NOISE * rng.standard_normal(points.shape), dtype=np.float64
    )


def sample_pinwheel(n: int, rng: np.random.Generator) -> Array:
    """Sample a five-arm pinwheel around its canonical arm centres."""
    return _sample_centred_mixture(n, rng, PINWHEEL_SAMPLER_CENTERS, PINWHEEL_NOISE)


def sample_checkerboard(n: int, rng: np.random.Generator) -> Array:
    """Sample the four-corner checkerboard mixture."""
    return _sample_centred_mixture(n, rng, CHECKERBOARD_SAMPLER_CENTERS, CHECKERBOARD_NOISE)


def sample_gaussian_grid(n: int, rng: np.random.Generator) -> Array:
    """Sample the canonical 5 by 5 Gaussian grid."""
    return _sample_centred_mixture(n, rng, GAUSSIAN_GRID_SAMPLER_CENTERS, GAUSSIAN_GRID_NOISE)


_SAMPLERS: dict[str, Sampler] = {
    "two_moons": sample_two_moons,
    "eight_gaussians": sample_eight_gaussians,
    "swiss_roll": sample_swiss_roll,
    "pinwheel": sample_pinwheel,
    "checkerboard": sample_checkerboard,
    "gaussian_grid": sample_gaussian_grid,
}
_SAMPLER_CENTERS: dict[str, Array] = {
    "two_moons": TWO_MOONS_SAMPLER_CENTERS,
    "eight_gaussians": EIGHT_GAUSSIANS_SAMPLER_CENTERS,
    "swiss_roll": SWISS_ROLL_SAMPLER_CENTERS,
    "pinwheel": PINWHEEL_SAMPLER_CENTERS,
    "checkerboard": CHECKERBOARD_SAMPLER_CENTERS,
    "gaussian_grid": GAUSSIAN_GRID_SAMPLER_CENTERS,
}
_MODE_CENTERS: dict[str, Array] = {
    "two_moons": TWO_MOONS_MODE_CENTERS,
    "eight_gaussians": EIGHT_GAUSSIANS_MODE_CENTERS,
    "swiss_roll": SWISS_ROLL_MODE_CENTERS,
    "pinwheel": PINWHEEL_MODE_CENTERS,
    "checkerboard": CHECKERBOARD_MODE_CENTERS,
    "gaussian_grid": GAUSSIAN_GRID_MODE_CENTERS,
}
_POSTERIOR_SHEETS: dict[str, tuple[float, float]] = {
    "two_moons": TWO_MOONS_POSTERIOR_SHEET,
    "eight_gaussians": EIGHT_GAUSSIANS_POSTERIOR_SHEET,
}
_POSTERIOR_CELLS: dict[str, tuple[tuple[float, float], ...]] = {
    "two_moons": TWO_MOONS_POSTERIOR_CELLS,
    "eight_gaussians": EIGHT_GAUSSIANS_POSTERIOR_CELLS,
}


def supported_targets() -> tuple[str, ...]:
    """Return every target with a registered analytic sampler."""
    return tuple(_SAMPLERS)


def sampler_for(target: str) -> Sampler:
    """Return the sampler for ``target`` or fail closed for an unknown name."""
    try:
        return _SAMPLERS[target]
    except KeyError as exc:
        raise ValueError(f"unknown_target:{target}") from exc


def sampler_centers_for(target: str) -> Array:
    """Return the canonical sampling geometry for ``target`` without copying it."""
    try:
        return _SAMPLER_CENTERS[target]
    except KeyError as exc:
        raise ValueError(f"unknown_target:{target}") from exc


def mode_centers_for_target(target: str) -> Array:
    """Return the canonical evaluation mode centres for ``target``."""
    try:
        return _MODE_CENTERS[target]
    except KeyError as exc:
        raise ValueError(f"unknown_target:{target}") from exc


def posterior_sheet_for(target: str) -> tuple[float, float]:
    """Return the canonical sheet centre for a supported posterior diagnostic target."""
    try:
        return _POSTERIOR_SHEETS[target]
    except KeyError as exc:
        raise ValueError(f"unknown_target:{target}") from exc


def posterior_cells_for(target: str) -> tuple[tuple[float, float], ...]:
    """Return the canonical isolated-cell centres for ``target``."""
    try:
        return _POSTERIOR_CELLS[target]
    except KeyError as exc:
        raise ValueError(f"unknown_target:{target}") from exc


def posterior_centers_for(target: str) -> Array:
    """Return the posterior sheet followed by its isolated cell centres."""
    return np.asarray((posterior_sheet_for(target), *posterior_cells_for(target)), dtype=np.float64)


__all__ = [name for name in globals() if name.isupper()] + [
    "mode_centers_for_target",
    "posterior_cells_for",
    "posterior_centers_for",
    "posterior_sheet_for",
    "sample_checkerboard",
    "sample_eight_gaussians",
    "sample_gaussian_grid",
    "sample_pinwheel",
    "sample_swiss_roll",
    "sample_two_moons",
    "sampler_centers_for",
    "sampler_for",
    "supported_targets",
]
