"""Canonical analytic target fixtures used by optional Flow Matching adapters."""

from .round2_targets import (
    ANISOTROPIC_GAUSSIAN_MIXTURE,
    HEAVY_TAILED,
    TARGET_REGISTRY,
    AnisotropicGaussianMixtureTarget,
    HeavyTailedTarget,
    build_target,
)
from .target_distributions import (
    EIGHT_GAUSSIANS_MODE_CENTERS,
    EIGHT_GAUSSIANS_SAMPLER_CENTERS,
    TWO_MOONS_MODE_CENTERS,
    TWO_MOONS_SAMPLER_CENTERS,
    mode_centers_for_target,
    sampler_centers_for,
    sampler_for,
    supported_targets,
)

__all__ = [
    "ANISOTROPIC_GAUSSIAN_MIXTURE",
    "EIGHT_GAUSSIANS_MODE_CENTERS",
    "EIGHT_GAUSSIANS_SAMPLER_CENTERS",
    "HEAVY_TAILED",
    "TARGET_REGISTRY",
    "TWO_MOONS_MODE_CENTERS",
    "TWO_MOONS_SAMPLER_CENTERS",
    "AnisotropicGaussianMixtureTarget",
    "HeavyTailedTarget",
    "build_target",
    "mode_centers_for_target",
    "sampler_centers_for",
    "sampler_for",
    "supported_targets",
]
