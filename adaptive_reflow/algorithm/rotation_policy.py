"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.perturbation.rotation_policy`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.rotation_policy import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .perturbation.rotation_policy import (
    ROTATION_POLICY_REGISTRY,
    BanditUCBRotationPolicy,
    RotationPolicy,
    RoundRobinRotationPolicy,
    build_rotation_policy,
)

__all__ = [
    "ROTATION_POLICY_REGISTRY",
    "BanditUCBRotationPolicy",
    "RotationPolicy",
    "RoundRobinRotationPolicy",
    "build_rotation_policy",
]
