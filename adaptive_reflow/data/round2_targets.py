"""Small deterministic target fixtures for round-two metric experiments."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

Array: TypeAlias = NDArray[np.float64]
ANISOTROPIC_GAUSSIAN_MIXTURE = "anisotropic_gaussian_mixture"
HEAVY_TAILED = "heavy_tailed"


def _validate_count(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name}_must_be_positive")
    return value


@dataclass(frozen=True)
class AnisotropicGaussianMixtureTarget:
    """A rotated 10:1 Gaussian mixture arranged around a unit circle."""

    n_modes: int = 8
    seed: int = 0

    def __post_init__(self) -> None:
        _validate_count(self.n_modes, name="n_modes")

    def sample(self, n: int, rng: np.random.Generator) -> Array:
        count = _validate_count(n, name="n")
        angles = np.arange(self.n_modes, dtype=np.float64) * (2.0 * np.pi / self.n_modes)
        centres = np.stack([2.0 * np.cos(angles), 2.0 * np.sin(angles)], axis=1)
        indices = rng.integers(0, self.n_modes, size=count)
        rotation = np.asarray(
            [
                [np.cos(np.pi / 6.0), -np.sin(np.pi / 6.0)],
                [np.sin(np.pi / 6.0), np.cos(np.pi / 6.0)],
            ],
            dtype=np.float64,
        )
        scale = np.asarray([[np.sqrt(0.25), 0.0], [0.0, np.sqrt(0.025)]], dtype=np.float64)
        noise = rng.standard_normal((count, 2)) @ (rotation @ scale).T
        return np.asarray(centres[indices] + noise, dtype=np.float64)


@dataclass(frozen=True)
class HeavyTailedTarget:
    """A radial mixture with Student-t perturbations for tail-sensitive metrics."""

    n_modes: int = 8
    seed: int = 0

    def __post_init__(self) -> None:
        _validate_count(self.n_modes, name="n_modes")

    def sample(self, n: int, rng: np.random.Generator) -> Array:
        count = _validate_count(n, name="n")
        angles = np.arange(self.n_modes, dtype=np.float64) * (2.0 * np.pi / self.n_modes)
        centres = np.stack([1.5 * np.cos(angles), 1.5 * np.sin(angles)], axis=1)
        indices = rng.integers(0, self.n_modes, size=count)
        return np.asarray(
            centres[indices] + 0.25 * rng.standard_t(df=3.0, size=(count, 2)), dtype=np.float64
        )


TargetFactory: TypeAlias = Callable[..., AnisotropicGaussianMixtureTarget | HeavyTailedTarget]
TARGET_REGISTRY: dict[str, TargetFactory] = {
    ANISOTROPIC_GAUSSIAN_MIXTURE: AnisotropicGaussianMixtureTarget,
    HEAVY_TAILED: HeavyTailedTarget,
}


def build_target(name: str, **kwargs: int) -> AnisotropicGaussianMixtureTarget | HeavyTailedTarget:
    """Build a named round-two target; unknown names remain a ``KeyError`` API."""
    return TARGET_REGISTRY[name](**kwargs)


__all__ = [
    "ANISOTROPIC_GAUSSIAN_MIXTURE",
    "HEAVY_TAILED",
    "TARGET_REGISTRY",
    "AnisotropicGaussianMixtureTarget",
    "HeavyTailedTarget",
    "build_target",
]
