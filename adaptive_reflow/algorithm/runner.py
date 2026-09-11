"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.runner.runner`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.runner import ...``
for downstream tools and tests.

Note: do not confuse this top-level shim with the
:mod:`adaptive_reflow.algorithm.runner` subpackage — both names exist
because Python's import system allows a module ``runner`` and a
subpackage ``runner/`` to coexist at the same level (the subpackage
takes precedence when imported as ``adaptive_reflow.algorithm.runner``).
"""

from __future__ import annotations

from .runner.runner import (
    FORWARD_NOISE_INJECTED,
    ReInferenceConfig,
    ReInferenceResult,
    ReInferenceRunner,
)

__all__ = [
    "FORWARD_NOISE_INJECTED",
    "ReInferenceConfig",
    "ReInferenceResult",
    "ReInferenceRunner",
]
