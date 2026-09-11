"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.perturbation.round2_extra`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.round2_extra import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .perturbation.round2_extra import (
    DUAL_TARGET_ADAPTIVE_FAMILY,
    MULTICHANNEL_CONSTANT_POLICY_FAMILY,
    MULTICHANNEL_JITTERED_FAMILY,
    DualTargetAdaptivePolicyDriver,
    MultiChannelConstantPolicyDriver,
    MultiChannelJitteredConstantScheduler,
)

__all__ = [
    "DUAL_TARGET_ADAPTIVE_FAMILY",
    "DualTargetAdaptivePolicyDriver",
    "MULTICHANNEL_CONSTANT_POLICY_FAMILY",
    "MULTICHANNEL_JITTERED_FAMILY",
    "MultiChannelConstantPolicyDriver",
    "MultiChannelJitteredConstantScheduler",
]
